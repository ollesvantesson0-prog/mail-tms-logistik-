"""Order intake endpoints: interpret a message, review, approve, and export orders."""

import csv
import io
from datetime import datetime
from typing import Any, Literal

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user, require_company_membership
from backend.app.db.session import get_db
from backend.app.models.entities import Order
from backend.app.modules.order_intake.interpreter import tolka_meddelande

router = APIRouter(prefix="/api/companies/{company_id}/orders", tags=["orders"])

OrderStatus = Literal["pending", "approved", "discarded"]


class InterpretRequest(BaseModel):
    meddelande: str = Field(min_length=1, max_length=20000)
    avsandare: str = Field(default="", max_length=320)
    mottagen: datetime


class UpdateOrderRequest(BaseModel):
    order: dict[str, Any]


class OrderOut(BaseModel):
    id: str
    status: str
    created_at: datetime
    meddelandetyp: str
    sammanfattning: str
    meddelande: dict[str, Any]
    order: dict[str, Any]


class InterpretResponse(BaseModel):
    meddelandetyp: str
    sammanfattning: str
    ordrar: list[OrderOut]


def to_out(order: Order) -> OrderOut:
    return OrderOut(
        id=order.id,
        status=order.status,
        created_at=order.created_at,
        meddelandetyp=order.details.get("meddelandetyp", ""),
        sammanfattning=order.details.get("sammanfattning", ""),
        meddelande=order.details.get("meddelande", {}),
        order=order.details.get("order", {}),
    )


def require_member(request: Request, db: Session, company_id: str) -> None:
    user = get_current_user(request, db)
    require_company_membership(db, user.id, company_id)


def get_company_order(db: Session, company_id: str, order_id: str) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id, Order.company_id == company_id))
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ordern hittades inte.")
    return order


def require_pending(order: Order) -> None:
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ordern är redan granskad och kan inte ändras.",
        )


@router.post("/interpret", response_model=InterpretResponse, status_code=status.HTTP_201_CREATED)
def interpret_message(
    company_id: str,
    body: InterpretRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> InterpretResponse:
    require_member(request, db, company_id)
    try:
        resultat = tolka_meddelande(body.meddelande, body.avsandare, body.mottagen)
    except anthropic.AuthenticationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI-tolkningen saknar en giltig ANTHROPIC_API_KEY.",
        ) from error
    except (anthropic.APIError, RuntimeError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI-tolkningen misslyckades: {error}",
        ) from error

    meddelande = {
        "text": body.meddelande,
        "avsandare": body.avsandare,
        "mottagen": body.mottagen.isoformat(),
    }
    # Varje tolkad order blir en egen rad som granskas separat.
    orders = [
        Order(
            company_id=company_id,
            status="pending",
            details={
                "meddelandetyp": resultat["meddelandetyp"],
                "sammanfattning": resultat["sammanfattning"],
                "meddelande": meddelande,
                "order": tolkad_order,
            },
        )
        for tolkad_order in resultat["ordrar"]
    ]
    db.add_all(orders)
    db.commit()
    for order in orders:
        db.refresh(order)

    return InterpretResponse(
        meddelandetyp=resultat["meddelandetyp"],
        sammanfattning=resultat["sammanfattning"],
        ordrar=[to_out(order) for order in orders],
    )


@router.get("", response_model=list[OrderOut])
def list_orders(
    company_id: str,
    request: Request,
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> list[OrderOut]:
    require_member(request, db, company_id)
    query = select(Order).where(Order.company_id == company_id).order_by(Order.created_at.desc())
    if status_filter is not None:
        query = query.where(Order.status == status_filter)
    return [to_out(order) for order in db.scalars(query)]


CSV_COLUMNS = ["id", "status", "kund", "kundreferens", "fran", "till", "datum", "gods"]


def csv_row(order: Order) -> dict[str, str]:
    data = order.details.get("order", {})
    upphamtning = data.get("upphamtning", {})
    leveranser = data.get("leveranser", [])
    gods = data.get("gods", [])
    return {
        "id": order.id,
        "status": order.status,
        "kund": data.get("kund", {}).get("foretag", ""),
        "kundreferens": data.get("kundreferens", ""),
        "fran": upphamtning.get("ort", ""),
        "till": "; ".join(leverans.get("ort", "") for leverans in leveranser),
        "datum": upphamtning.get("datum", ""),
        "gods": "; ".join(
            f"{rad.get('antal') or ''} {rad.get('typ', '')} {rad.get('beskrivning', '')}".strip()
            for rad in gods
        ),
    }


@router.get("/export.csv")
def export_orders_csv(
    company_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    require_member(request, db, company_id)
    orders = db.scalars(
        select(Order)
        .where(Order.company_id == company_id, Order.status == "approved")
        .order_by(Order.created_at)
    )
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    writer.writerows(csv_row(order) for order in orders)
    return Response(
        # BOM så att Excel visar å, ä och ö rätt.
        content="﻿" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="ordrar.csv"'},
    )


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    company_id: str,
    order_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> OrderOut:
    require_member(request, db, company_id)
    return to_out(get_company_order(db, company_id, order_id))


@router.put("/{order_id}", response_model=OrderOut)
def update_order(
    company_id: str,
    order_id: str,
    body: UpdateOrderRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> OrderOut:
    require_member(request, db, company_id)
    order = get_company_order(db, company_id, order_id)
    require_pending(order)
    # Tilldela en ny dict så att SQLAlchemy märker att JSON-fältet ändrats.
    order.details = {**order.details, "order": body.order}
    db.commit()
    return to_out(order)


def set_status(db: Session, company_id: str, order_id: str, new_status: str) -> OrderOut:
    order = get_company_order(db, company_id, order_id)
    require_pending(order)
    order.status = new_status
    db.commit()
    return to_out(order)


@router.post("/{order_id}/approve", response_model=OrderOut)
def approve_order(
    company_id: str,
    order_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> OrderOut:
    require_member(request, db, company_id)
    return set_status(db, company_id, order_id, "approved")


@router.post("/{order_id}/discard", response_model=OrderOut)
def discard_order(
    company_id: str,
    order_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> OrderOut:
    require_member(request, db, company_id)
    return set_status(db, company_id, order_id, "discarded")
