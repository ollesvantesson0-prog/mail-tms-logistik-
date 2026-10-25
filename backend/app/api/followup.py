"""
Follow-up: everything the dispatcher should look at right now.

Rules are fixed (not AI): unhandled deviations and delays, jobs past their time
windows, and today's jobs missing a vehicle or driver.
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.orders import OrderOut, require_member, to_out
from backend.app.db.session import get_db
from backend.app.models.entities import Order
from backend.app.modules.planning.checks import order_datum

router = APIRouter(prefix="/api/companies/{company_id}/followup", tags=["followup"])

Severity = Literal["hog", "medel"]


class FollowupItem(BaseModel):
    typ: str
    allvarlighet: Severity
    rubrik: str
    text: str
    order: OrderOut
    event_id: str | None = None


class DaySummary(BaseModel):
    jobb: int
    ej_paborjade: int
    hamtade: int
    levererade: int
    vantar_granskning: int


class Followup(BaseModel):
    items: list[FollowupItem]
    idag: DaySummary
    # Dagens levererade jobb, för att kunna skicka leveransbesked.
    levererade: list[OrderOut]


def senaste_leveranstid(order: dict) -> str:
    tider = [plats.get("tid_till", "") for plats in order.get("leveranser", []) if plats.get("tid_till")]
    return max(tider, default="")


@router.get("", response_model=Followup)
def followup(company_id: str, nu: datetime, request: Request, db: Session = Depends(get_db)) -> Followup:
    """`nu` är webbläsarens lokala tid, t.ex. 2026-10-29T10:15, så att tidsfönstren jämförs rätt."""
    require_member(request, db, company_id)
    orders = list(
        db.scalars(select(Order).where(Order.company_id == company_id, Order.status == "approved"))
    )
    idag = nu.date().isoformat()
    klockan = nu.strftime("%H:%M")
    items: list[FollowupItem] = []

    for order in orders:
        data = order.details["order"]
        kund = data.get("kund", {}).get("foretag") or "Okänd kund"
        out = None

        def item(typ: str, allvarlighet: Severity, rubrik: str, text: str, event_id: str | None = None) -> None:
            nonlocal out
            out = out or to_out(order, db)
            items.append(
                FollowupItem(typ=typ, allvarlighet=allvarlighet, rubrik=rubrik, text=text, order=out, event_id=event_id)
            )

        # Förarens rapporter som ingen har tagit hand om än, oavsett dag.
        for event in order.events:
            if event.handled_at is not None:
                continue
            forare = event.driver.name if event.driver else "Föraren"
            if event.type == "deviation":
                item("avvikelse", "hog", f"Avvikelse: {kund}", f"{forare}: {event.note or 'se foto'}", event.id)
            elif event.type == "delay":
                item("forsening", "medel", f"Försening: {kund}", f"{forare}: {event.note}", event.id)

        if order_datum(data) != idag:
            continue
        upp_till = data.get("upphamtning", {}).get("tid_till", "")
        lev_till = senaste_leveranstid(data)
        if order.vehicle_id is None:
            # Ett oplanerat jobb är en punkt; den blir brådskande när hämttiden har passerat.
            sent = bool(upp_till) and klockan > upp_till
            item(
                "ej_planerad",
                "hog" if sent else "medel",
                f"Ej planerad: {kund}",
                f"Skulle hämtas senast {upp_till} men har ingen bil." if sent else "Jobbet ska köras idag men har ingen bil.",
            )
            continue
        if order.driver_id is None:
            item("saknar_forare", "medel", f"Saknar förare: {kund}", "Bilen är vald men ingen förare.")
        if order.execution_status is None and upp_till and klockan > upp_till:
            item(
                "sen_upphamtning",
                "hog",
                f"Ej hämtat: {kund}",
                f"Skulle hämtas senast {upp_till}, men föraren har inte rapporterat hämtat.",
            )
        if order.execution_status != "delivered" and lev_till and klockan > lev_till:
            item(
                "sen_leverans",
                "hog",
                f"Ej levererat: {kund}",
                f"Skulle vara levererat senast {lev_till}, men föraren har inte rapporterat levererat.",
            )

    items.sort(key=lambda row: row.allvarlighet != "hog")
    todays = [order for order in orders if order_datum(order.details["order"]) == idag]
    pending = db.scalar(
        select(func.count()).select_from(Order).where(Order.company_id == company_id, Order.status == "pending")
    )
    return Followup(
        items=items,
        idag=DaySummary(
            jobb=len(todays),
            ej_paborjade=sum(order.execution_status is None for order in todays),
            hamtade=sum(order.execution_status == "picked_up" for order in todays),
            levererade=sum(order.execution_status == "delivered" for order in todays),
            vantar_granskning=pending or 0,
        ),
        levererade=[to_out(order, db) for order in todays if order.execution_status == "delivered"],
    )
