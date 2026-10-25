"""Order intake endpoints: interpret, review, approve, assign, and export orders."""

import csv
import io
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Literal

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user, require_company_membership
from backend.app.db.session import get_db
from backend.app.models.entities import Company, Driver, Order, OrderEvent, Vehicle, as_utc
from backend.app.modules.order_intake.changes import forandringar, hitta_mal_order, sla_ihop
from backend.app.modules.order_intake.interpreter import tolka_meddelande
from backend.app.modules.order_intake.reply import skriv_svar

router = APIRouter(prefix="/api/companies/{company_id}/orders", tags=["orders"])

# applied = en ändring/avbokning som har genomförts på sin målorder.
OrderStatus = Literal["pending", "approved", "discarded", "applied", "cancelled"]
CHANGE_TYPES = ("andring", "avbokning")


class InterpretRequest(BaseModel):
    meddelande: str = Field(min_length=1, max_length=20000)
    avsandare: str = Field(default="", max_length=320)
    mottagen: datetime


class UpdateOrderRequest(BaseModel):
    order: dict[str, Any]


class TargetRequest(BaseModel):
    mal_order_id: str | None


class AssignmentRequest(BaseModel):
    vehicle_id: str | None = None
    driver_id: str | None = None


class OrderOut(BaseModel):
    id: str
    status: str
    created_at: datetime
    meddelandetyp: str
    sammanfattning: str
    meddelande: dict[str, Any]
    order: dict[str, Any]
    vehicle_id: str | None
    vehicle_registration: str | None
    driver_id: str | None
    driver_name: str | None
    # Bara för ändringar och avbokningar: ordern som meddelandet gäller.
    mal_order: dict[str, Any] | None
    forandringar: list[dict[str, str]]
    historik: list[dict[str, Any]]
    svarsutkast: dict[str, str] | None
    # Förarens rapporter: hämtat, levererat och avvikelser.
    execution_status: str | None
    events: list[dict[str, Any]]


class InterpretResponse(BaseModel):
    meddelandetyp: str
    sammanfattning: str
    ordrar: list[OrderOut]


def is_change(order: Order) -> bool:
    return order.details.get("meddelandetyp") in CHANGE_TYPES


def target_of(db: Session, order: Order) -> Order | None:
    mal_order_id = order.details.get("mal_order_id")
    if not mal_order_id:
        return None
    return db.scalar(
        select(Order).where(Order.id == mal_order_id, Order.company_id == order.company_id)
    )


def target_summary(target: Order) -> dict[str, Any]:
    row = csv_row(target)
    return {falt: row[falt] for falt in ("id", "status", "kund", "kundreferens", "fran", "till", "datum")}


def to_out(order: Order, db: Session) -> OrderOut:
    target = target_of(db, order) if is_change(order) else None
    show_diff = target is not None and order.details["meddelandetyp"] == "andring"
    return OrderOut(
        id=order.id,
        status=order.status,
        created_at=order.created_at,
        meddelandetyp=order.details.get("meddelandetyp", ""),
        sammanfattning=order.details.get("sammanfattning", ""),
        meddelande=order.details.get("meddelande", {}),
        order=order.details.get("order", {}),
        vehicle_id=order.vehicle_id,
        vehicle_registration=order.vehicle.registration_number if order.vehicle else None,
        driver_id=order.driver_id,
        driver_name=order.driver.name if order.driver else None,
        mal_order=target_summary(target) if target else None,
        forandringar=(
            forandringar(target.details["order"], order.details["order"]) if show_diff else []
        ),
        historik=order.details.get("historik", []),
        svarsutkast=order.details.get("svarsutkast"),
        execution_status=order.execution_status,
        events=[
            {
                "id": event.id,
                "type": event.type,
                "note": event.note,
                "created_at": as_utc(event.created_at),
                "driver_name": event.driver.name if event.driver else None,
                "has_photo": event.photo_type is not None,
            }
            for event in order.events
        ],
    )


def require_member(request: Request, db: Session, company_id: str) -> None:
    user = get_current_user(request, db)
    require_company_membership(db, user.id, company_id)


def get_company_order(db: Session, company_id: str, order_id: str) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id, Order.company_id == company_id))
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ordern hittades inte.")
    return order


def target_candidates(db: Session, company_id: str) -> list[Order]:
    """Ordrar som en ändring eller avbokning kan gälla."""
    orders = db.scalars(
        select(Order).where(
            Order.company_id == company_id, Order.status.in_(("pending", "approved"))
        )
    )
    return [order for order in orders if not is_change(order)]


def require_pending(order: Order) -> None:
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ordern är redan granskad och kan inte ändras.",
        )


@contextmanager
def ai_errors(namn: str) -> Iterator[None]:
    """Gör om fel från Claude-anrop till begripliga HTTP-fel."""
    try:
        yield
    except anthropic.AuthenticationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{namn} saknar en giltig ANTHROPIC_API_KEY.",
        ) from error
    except (anthropic.APIError, RuntimeError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{namn} misslyckades: {error}",
        ) from error


@router.post("/interpret", response_model=InterpretResponse, status_code=status.HTTP_201_CREATED)
def interpret_message(
    company_id: str,
    body: InterpretRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> InterpretResponse:
    require_member(request, db, company_id)
    with ai_errors("AI-tolkningen"):
        resultat = tolka_meddelande(body.meddelande, body.avsandare, body.mottagen)

    meddelande = {
        "text": body.meddelande,
        "avsandare": body.avsandare,
        "mottagen": body.mottagen.isoformat(),
    }
    kandidater = []
    if resultat["meddelandetyp"] in CHANGE_TYPES:
        kandidater = [
            (order.id, order.status, order.details["order"])
            for order in target_candidates(db, company_id)
        ]

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
                # Ändringar och avbokningar kopplas till ordern de gäller om den hittas.
                "mal_order_id": hitta_mal_order(tolkad_order["galler_order"], kandidater),
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
        ordrar=[to_out(order, db) for order in orders],
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
    return [to_out(order, db) for order in db.scalars(query)]


CSV_COLUMNS = [
    "id", "status", "kund", "kundreferens", "fran", "till", "datum", "gods", "fordon", "forare",
]


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
        # Ort i första hand, annars företagsnamnet (t.ex. "Coop Tuve" utan adress).
        "till": "; ".join(
            leverans.get("ort") or leverans.get("foretag", "") for leverans in leveranser
        ),
        # Upphämtningsdatum, annars första leveransdatumet.
        "datum": upphamtning.get("datum")
        or next((leverans["datum"] for leverans in leveranser if leverans.get("datum")), ""),
        "gods": "; ".join(
            f"{rad.get('antal') or ''} {rad.get('typ', '')} {rad.get('beskrivning', '')}".strip()
            for rad in gods
        ),
        "fordon": order.vehicle.registration_number if order.vehicle else "",
        "forare": order.driver.name if order.driver else "",
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
        content="\ufeff" + buffer.getvalue(),
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
    return to_out(get_company_order(db, company_id, order_id), db)


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
    return to_out(order, db)


@router.put("/{order_id}/target", response_model=OrderOut)
def set_target(
    company_id: str,
    order_id: str,
    body: TargetRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> OrderOut:
    """Välj för hand vilken order en ändring eller avbokning gäller."""
    require_member(request, db, company_id)
    order = get_company_order(db, company_id, order_id)
    require_pending(order)
    if not is_change(order):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bara ändringar och avbokningar gäller en annan order.",
        )
    if body.mal_order_id is not None and body.mal_order_id not in {
        candidate.id for candidate in target_candidates(db, company_id)
    }:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Målordern hittades inte.")
    order.details = {**order.details, "mal_order_id": body.mal_order_id}
    db.commit()
    return to_out(order, db)


def apply_change(db: Session, change: Order) -> None:
    """Genomför en ändring eller avbokning på målordern och sparar det i dess historik."""
    target = target_of(db, change)
    if target is None or target.status not in ("pending", "approved") or is_change(target):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Välj vilken order ändringen gäller innan du godkänner.",
        )
    typ = change.details["meddelandetyp"]
    handelse: dict[str, Any] = {
        "typ": typ,
        "andring_id": change.id,
        "tid": datetime.now(timezone.utc).isoformat(),
        "sammanfattning": change.details.get("sammanfattning", ""),
    }
    details = dict(target.details)
    if typ == "andring":
        handelse["forandringar"] = forandringar(details["order"], change.details["order"])
        details["order"] = sla_ihop(details["order"], change.details["order"])
    else:
        target.status = "cancelled"
    details["historik"] = [*details.get("historik", []), handelse]
    target.details = details
    change.status = "applied"


def set_status(db: Session, company_id: str, order_id: str, new_status: str) -> OrderOut:
    order = get_company_order(db, company_id, order_id)
    require_pending(order)
    if new_status == "approved" and is_change(order):
        apply_change(db, order)
    else:
        order.status = new_status
    db.commit()
    return to_out(order, db)


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


def check_assignable(
    db: Session,
    model: type[Vehicle] | type[Driver],
    company_id: str,
    resource_id: str | None,
    current_id: str | None,
    name: str,
) -> None:
    """Fordonet/föraren måste tillhöra åkeriet och vara aktiv (om det inte redan är tilldelat)."""
    if resource_id is None or resource_id == current_id:
        return
    resource = db.scalar(select(model).where(model.id == resource_id, model.company_id == company_id))
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} hittades inte.")
    if not resource.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"{name} är inaktiv och kan inte tilldelas."
        )


@router.put("/{order_id}/assignment", response_model=OrderOut)
def assign_order(
    company_id: str,
    order_id: str,
    body: AssignmentRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> OrderOut:
    require_member(request, db, company_id)
    order = get_company_order(db, company_id, order_id)
    if order.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bara godkända ordrar kan få fordon och förare.",
        )
    check_assignable(db, Vehicle, company_id, body.vehicle_id, order.vehicle_id, "Fordonet")
    check_assignable(db, Driver, company_id, body.driver_id, order.driver_id, "Föraren")
    order.vehicle_id = body.vehicle_id
    order.driver_id = body.driver_id
    db.commit()
    # Läs om relationerna så att svaret visar det nya fordonet och den nya föraren.
    db.refresh(order)
    return to_out(order, db)


@router.post("/{order_id}/reply-draft", response_model=OrderOut)
def create_reply_draft(
    company_id: str,
    order_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> OrderOut:
    """Låter AI:n skriva ett svarsutkast till kunden. Inget skickas automatiskt."""
    require_member(request, db, company_id)
    order = get_company_order(db, company_id, order_id)
    company = db.get(Company, company_id)
    target = target_of(db, order) if is_change(order) else None
    with ai_errors("Svarsutkastet"):
        utkast = skriv_svar(
            meddelande=order.details.get("meddelande", {}),
            meddelandetyp=order.details.get("meddelandetyp", ""),
            order=order.details.get("order", {}),
            akeri=company.name,
            forandringar=(
                forandringar(target.details["order"], order.details["order"]) if target else None
            ),
        )
    order.details = {
        **order.details,
        "svarsutkast": {**utkast, "skapad": datetime.now(timezone.utc).isoformat()},
    }
    db.commit()
    return to_out(order, db)


@router.get("/{order_id}/events/{event_id}/photo")
def event_photo(
    company_id: str,
    order_id: str,
    event_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Fotot som föraren tog vid en avvikelse."""
    require_member(request, db, company_id)
    order = get_company_order(db, company_id, order_id)
    event = db.scalar(
        select(OrderEvent).where(OrderEvent.id == event_id, OrderEvent.order_id == order.id)
    )
    if event is None or event.photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fotot hittades inte.")
    return Response(content=event.photo, media_type=event.photo_type)
