"""Fleet endpoints: the company's vehicles and drivers."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, StringConstraints
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user, require_company_membership
from backend.app.db.session import get_db
from backend.app.models.entities import Driver, Vehicle

router = APIRouter(prefix="/api/companies/{company_id}", tags=["fleet"])

Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


class VehicleIn(BaseModel):
    registration_number: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=2, max_length=20)
    ]
    description: Text = ""
    is_active: bool = True


class VehicleOut(BaseModel):
    id: str
    registration_number: str
    description: str
    is_active: bool


class DriverIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)] = ""
    is_active: bool = True


class DriverOut(BaseModel):
    id: str
    name: str
    phone: str
    is_active: bool


def require_member(request: Request, db: Session, company_id: str) -> None:
    user = get_current_user(request, db)
    require_company_membership(db, user.id, company_id)


def normalize_registration(value: str) -> str:
    """'abc 123' och 'ABC123' ska räknas som samma bil."""
    return re.sub(r"[\s-]", "", value).upper()


def vehicle_out(vehicle: Vehicle) -> VehicleOut:
    return VehicleOut(
        id=vehicle.id,
        registration_number=vehicle.registration_number,
        description=vehicle.description,
        is_active=vehicle.is_active,
    )


def driver_out(driver: Driver) -> DriverOut:
    return DriverOut(id=driver.id, name=driver.name, phone=driver.phone, is_active=driver.is_active)


def save_vehicle(db: Session, vehicle: Vehicle, body: VehicleIn) -> VehicleOut:
    registration_number = normalize_registration(body.registration_number)
    vehicle.registration_number = registration_number
    vehicle.description = body.description
    vehicle.is_active = body.is_active
    try:
        db.add(vehicle)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Fordonet {registration_number} finns redan.",
        ) from error
    return vehicle_out(vehicle)


def get_company_vehicle(db: Session, company_id: str, vehicle_id: str) -> Vehicle:
    vehicle = db.scalar(
        select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.company_id == company_id)
    )
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fordonet hittades inte.")
    return vehicle


def get_company_driver(db: Session, company_id: str, driver_id: str) -> Driver:
    driver = db.scalar(select(Driver).where(Driver.id == driver_id, Driver.company_id == company_id))
    if driver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Föraren hittades inte.")
    return driver


@router.get("/vehicles", response_model=list[VehicleOut])
def list_vehicles(company_id: str, request: Request, db: Session = Depends(get_db)) -> list[VehicleOut]:
    require_member(request, db, company_id)
    vehicles = db.scalars(
        select(Vehicle).where(Vehicle.company_id == company_id).order_by(Vehicle.registration_number)
    )
    return [vehicle_out(vehicle) for vehicle in vehicles]


@router.post("/vehicles", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    company_id: str,
    body: VehicleIn,
    request: Request,
    db: Session = Depends(get_db),
) -> VehicleOut:
    require_member(request, db, company_id)
    return save_vehicle(db, Vehicle(company_id=company_id), body)


@router.put("/vehicles/{vehicle_id}", response_model=VehicleOut)
def update_vehicle(
    company_id: str,
    vehicle_id: str,
    body: VehicleIn,
    request: Request,
    db: Session = Depends(get_db),
) -> VehicleOut:
    require_member(request, db, company_id)
    return save_vehicle(db, get_company_vehicle(db, company_id, vehicle_id), body)


@router.get("/drivers", response_model=list[DriverOut])
def list_drivers(company_id: str, request: Request, db: Session = Depends(get_db)) -> list[DriverOut]:
    require_member(request, db, company_id)
    drivers = db.scalars(select(Driver).where(Driver.company_id == company_id).order_by(Driver.name))
    return [driver_out(driver) for driver in drivers]


@router.post("/drivers", response_model=DriverOut, status_code=status.HTTP_201_CREATED)
def create_driver(
    company_id: str,
    body: DriverIn,
    request: Request,
    db: Session = Depends(get_db),
) -> DriverOut:
    require_member(request, db, company_id)
    driver = Driver(company_id=company_id, name=body.name, phone=body.phone, is_active=body.is_active)
    db.add(driver)
    db.commit()
    return driver_out(driver)


@router.put("/drivers/{driver_id}", response_model=DriverOut)
def update_driver(
    company_id: str,
    driver_id: str,
    body: DriverIn,
    request: Request,
    db: Session = Depends(get_db),
) -> DriverOut:
    require_member(request, db, company_id)
    driver = get_company_driver(db, company_id, driver_id)
    driver.name = body.name
    driver.phone = body.phone
    driver.is_active = body.is_active
    db.commit()
    return driver_out(driver)
