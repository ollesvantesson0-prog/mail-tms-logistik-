"""
Driver endpoints, reached through the driver's personal link instead of a login.

The token in the URL is the driver's key. Only its hash is stored, and a driver
only ever sees jobs assigned to them.
"""

import base64
import binascii
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.fleet import hash_token
from backend.app.db.session import get_db
from backend.app.models.entities import Company, Driver, Order, OrderEvent, as_utc
from backend.app.modules.planning.checks import order_datum

router = APIRouter(prefix="/api/driver/{token}", tags=["driver"])

MAX_PHOTO_BYTES = 3 * 1024 * 1024
PHOTO_TYPES = ("image/jpeg", "image/png", "image/webp")


class EventIn(BaseModel):
    type: Literal["picked_up", "delivered", "deviation", "delay"]
    note: str = Field(default="", max_length=2000)
    # Fotot skickas som base64-text så att formuläret kan vara vanlig JSON.
    photo_base64: str | None = Field(default=None, max_length=MAX_PHOTO_BYTES * 2)
    photo_type: str | None = None


class EventOut(BaseModel):
    id: str
    type: str
    note: str
    created_at: Any
    has_photo: bool


class DriverJob(BaseModel):
    id: str
    vehicle: str | None
    kund: dict[str, Any]
    kundreferens: str
    upphamtning: dict[str, Any]
    leveranser: list[dict[str, Any]]
    gods: list[dict[str, Any]]
    krav: dict[str, Any]
    execution_status: str | None
    events: list[EventOut]


class DriverDay(BaseModel):
    driver: str
    company: str
    datum: date
    jobb: list[DriverJob]


def event_out(event: OrderEvent) -> EventOut:
    return EventOut(
        id=event.id,
        type=event.type,
        note=event.note,
        created_at=as_utc(event.created_at),
        has_photo=event.photo_type is not None,
    )


def driver_from_token(db: Session, token: str) -> Driver:
    driver = db.scalar(select(Driver).where(Driver.access_token_hash == hash_token(token)))
    if driver is None or not driver.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Länken fungerar inte längre. Be trafikledaren om en ny.",
        )
    return driver


def job_out(order: Order) -> DriverJob:
    data = order.details["order"]
    return DriverJob(
        id=order.id,
        vehicle=order.vehicle.registration_number if order.vehicle else None,
        kund=data.get("kund", {}),
        kundreferens=data.get("kundreferens", ""),
        upphamtning=data.get("upphamtning", {}),
        leveranser=data.get("leveranser", []),
        gods=data.get("gods", []),
        krav=data.get("krav", {}),
        execution_status=order.execution_status,
        events=[event_out(event) for event in order.events],
    )


def start_time(order: Order) -> str:
    plats = order.details["order"].get("upphamtning", {})
    return plats.get("tid_fran") or plats.get("tid_till") or "99:99"


@router.get("", response_model=DriverDay)
def driver_day(token: str, datum: date | None = None, db: Session = Depends(get_db)) -> DriverDay:
    driver = driver_from_token(db, token)
    datum = datum or date.today()
    orders = db.scalars(
        select(Order).where(Order.driver_id == driver.id, Order.status == "approved")
    )
    jobb = sorted(
        (order for order in orders if order_datum(order.details["order"]) == datum.isoformat()),
        key=start_time,
    )
    return DriverDay(
        driver=driver.name,
        company=db.get(Company, driver.company_id).name,
        datum=datum,
        jobb=[job_out(order) for order in jobb],
    )


@router.post("/jobs/{order_id}/events", response_model=DriverJob, status_code=status.HTTP_201_CREATED)
def report_event(token: str, order_id: str, body: EventIn, db: Session = Depends(get_db)) -> DriverJob:
    driver = driver_from_token(db, token)
    order = db.scalar(
        select(Order).where(
            Order.id == order_id, Order.driver_id == driver.id, Order.status == "approved"
        )
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jobbet finns inte på din lista.")

    photo = None
    if body.photo_base64:
        if body.photo_type not in PHOTO_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fotot måste vara en bild.")
        try:
            photo = base64.b64decode(body.photo_base64, validate=True)
        except binascii.Error as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fotot är skadat.") from error
        if len(photo) > MAX_PHOTO_BYTES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fotot är för stort.")
    if body.type == "deviation" and not body.note.strip() and photo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Beskriv avvikelsen eller ta ett foto.",
        )
    if body.type == "delay" and not body.note.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skriv hur sen du blir, t.ex. \"ca 30 min, kö på E6\".",
        )

    db.add(
        OrderEvent(
            order_id=order.id,
            driver_id=driver.id,
            type=body.type,
            note=body.note.strip(),
            photo=photo,
            photo_type=body.photo_type if photo else None,
        )
    )
    if body.type in ("picked_up", "delivered"):
        order.execution_status = body.type
    db.commit()
    db.refresh(order)
    return job_out(order)
