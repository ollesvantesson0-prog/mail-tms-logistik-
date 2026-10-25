"""Planning endpoints: a day's plan per vehicle and AI suggestions for unplanned jobs."""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.fleet import DriverOut, VehicleOut, driver_out, vehicle_out
from backend.app.api.orders import OrderOut, ai_errors, require_member, to_out
from backend.app.db.session import get_db
from backend.app.models.entities import Driver, Order, Vehicle
from backend.app.modules.planning.checks import (
    antal_pallar,
    kontrollera_bil,
    kontrollera_jobb,
    order_datum,
    total_vikt,
)
from backend.app.modules.planning.planner import foresla_plan, jobb_underlag

router = APIRouter(prefix="/api/companies/{company_id}/planning", tags=["planning"])


class PlannedJob(BaseModel):
    order: OrderOut
    varningar: list[str]


class VehicleDay(BaseModel):
    vehicle: VehicleOut
    ordrar: list[PlannedJob]
    vikt_kg: float
    pallar: int
    varningar: list[str]


class DayPlan(BaseModel):
    datum: date
    bilar: list[VehicleDay]
    ej_planerade: list[OrderOut]
    utan_datum: list[OrderOut]
    varningar: list[str]
    forare: list[DriverOut]


class SuggestRequest(BaseModel):
    datum: date


class Suggestion(BaseModel):
    order_id: str
    vehicle_id: str
    driver_id: str | None
    motivering: str
    varningar: list[str]


class Unplannable(BaseModel):
    order_id: str
    anledning: str


class SuggestResponse(BaseModel):
    forslag: list[Suggestion]
    ej_planerbara: list[Unplannable]
    sammanfattning: str


def start_time(order: Order) -> str:
    plats = order.details["order"].get("upphamtning", {})
    return plats.get("tid_fran") or plats.get("tid_till") or "99:99"


def approved_orders(db: Session, company_id: str) -> list[Order]:
    return list(
        db.scalars(select(Order).where(Order.company_id == company_id, Order.status == "approved"))
    )


def orders_on(orders: list[Order], datum: date) -> list[Order]:
    return sorted(
        (order for order in orders if order_datum(order.details["order"]) == datum.isoformat()),
        key=start_time,
    )


def fleet(db: Session, model: type[Vehicle] | type[Driver], company_id: str) -> list:
    return list(db.scalars(select(model).where(model.company_id == company_id)))


@router.get("", response_model=DayPlan)
def day_plan(company_id: str, datum: date, request: Request, db: Session = Depends(get_db)) -> DayPlan:
    require_member(request, db, company_id)
    orders = approved_orders(db, company_id)
    days_orders = orders_on(orders, datum)
    vehicles = fleet(db, Vehicle, company_id)
    drivers = fleet(db, Driver, company_id)

    bilar = []
    for vehicle in vehicles:
        jobb = [order for order in days_orders if order.vehicle_id == vehicle.id]
        # Inaktiva bilar visas bara om de redan har jobb den dagen.
        if not vehicle.is_active and not jobb:
            continue
        data = [order.details["order"] for order in jobb]
        bilar.append(
            VehicleDay(
                vehicle=vehicle_out(vehicle),
                ordrar=[
                    PlannedJob(
                        order=to_out(order, db),
                        varningar=kontrollera_jobb(order.details["order"], vehicle, order.driver),
                    )
                    for order in jobb
                ],
                vikt_kg=sum(total_vikt(order) for order in data),
                pallar=sum(antal_pallar(order) for order in data),
                varningar=kontrollera_bil(data, vehicle, [order.driver for order in jobb if order.driver]),
            )
        )

    # En förare kan inte köra två bilar samma dag.
    bilar_per_forare: dict[str, set[str]] = {}
    for order in days_orders:
        if order.driver and order.vehicle:
            bilar_per_forare.setdefault(order.driver.name, set()).add(order.vehicle.registration_number)
    varningar = [
        f"{namn} är planerad på flera bilar: {', '.join(sorted(regs))}."
        for namn, regs in sorted(bilar_per_forare.items())
        if len(regs) > 1
    ]

    return DayPlan(
        datum=datum,
        bilar=bilar,
        ej_planerade=[to_out(order, db) for order in days_orders if order.vehicle_id is None],
        utan_datum=[
            to_out(order, db)
            for order in orders
            if order.vehicle_id is None and not order_datum(order.details["order"])
        ],
        varningar=varningar,
        forare=[driver_out(driver) for driver in drivers],
    )


def vehicle_info(vehicle: Vehicle) -> dict[str, Any]:
    return {
        "id": vehicle.id,
        "regnr": vehicle.registration_number,
        "beskrivning": vehicle.description,
        "max_vikt_kg": vehicle.max_weight_kg,
        "pallplatser": vehicle.pallet_places,
        "kyl": vehicle.has_cooling,
        "bakgavellyft": vehicle.has_tail_lift,
        "kran": vehicle.has_crane,
        "adr": vehicle.adr_approved,
    }


@router.post("/suggest", response_model=SuggestResponse)
def suggest_plan(
    company_id: str,
    body: SuggestRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> SuggestResponse:
    """AI-förslag för dagens oplanerade jobb. Inget sparas; förslagen godkänns i planeringsvyn."""
    require_member(request, db, company_id)
    days_orders = orders_on(approved_orders(db, company_id), body.datum)
    unplanned = [order for order in days_orders if order.vehicle_id is None]
    vehicles = {v.id: v for v in fleet(db, Vehicle, company_id) if v.is_active}
    drivers = {d.id: d for d in fleet(db, Driver, company_id) if d.is_active}

    if not unplanned:
        return SuggestResponse(forslag=[], ej_planerbara=[], sammanfattning="Inga oplanerade jobb den här dagen.")
    if not vehicles:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lägg in minst ett aktivt fordon under Flotta först.",
        )

    planned = [
        {
            **jobb_underlag(order.id, order.details["order"]),
            "vehicle_id": order.vehicle_id,
            "driver_id": order.driver_id,
        }
        for order in days_orders
        if order.vehicle_id is not None
    ]
    with ai_errors("Planeringen"):
        resultat = foresla_plan(
            datum=body.datum.isoformat(),
            fordon=[vehicle_info(vehicle) for vehicle in vehicles.values()],
            forare=[
                {"id": d.id, "namn": d.name, "adr_behorighet": d.has_adr_license}
                for d in drivers.values()
            ],
            planerade=planned,
            oplanerade=[(order.id, order.details["order"]) for order in unplanned],
        )

    by_id = {order.id: order for order in unplanned}
    forslag: list[Suggestion] = []
    seen: set[str] = set()
    for rad in resultat["forslag"]:
        if rad["order_id"] in seen:
            continue
        seen.add(rad["order_id"])
        vehicle = vehicles[rad["vehicle_id"]]
        driver = drivers.get(rad["driver_id"])
        forslag.append(
            Suggestion(
                order_id=rad["order_id"],
                vehicle_id=vehicle.id,
                driver_id=driver.id if driver else None,
                motivering=rad["motivering"],
                # Kontrollera AI:ns förslag mot de fasta reglerna.
                varningar=kontrollera_jobb(by_id[rad["order_id"]].details["order"], vehicle, driver),
            )
        )
    return SuggestResponse(
        forslag=forslag,
        ej_planerbara=[Unplannable(**rad) for rad in resultat["ej_planerbara"] if rad["order_id"] not in seen],
        sammanfattning=resultat["sammanfattning"],
    )
