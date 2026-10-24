"""Local account registration, login, and company membership endpoints."""

import os
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field, StringConstraints
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.security import (
    clear_session,
    create_session,
    get_current_user,
    hash_password,
    require_company_membership,
    verify_password,
)
from backend.app.db.session import get_db
from backend.app.models.entities import Company, Membership, User, UserSession

router = APIRouter(prefix="/api/auth", tags=["authentication"])
companies_router = APIRouter(prefix="/api/companies", tags=["companies"])


class RegisterRequest(BaseModel):
    company_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)
    ]
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserSummary(BaseModel):
    id: str
    email: str


class MembershipSummary(BaseModel):
    company_id: str
    company_name: str
    role: str


class AccountSummary(BaseModel):
    user: UserSummary
    companies: list[MembershipSummary]


@router.post("/register", response_model=AccountSummary, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AccountSummary:
    if os.getenv("APP_ENV") == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Självregistrering är bara aktiverad i lokal utveckling.",
        )
    email = str(body.email).lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-postadressen används redan.")

    company = Company(name=body.company_name)
    user = User(email=email, password_hash=hash_password(body.password))
    try:
        db.add_all([company, user])
        db.flush()
        membership = Membership(company_id=company.id, user_id=user.id, role="owner")
        db.add(membership)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kontot kunde inte skapas. Kontrollera att e-postadressen inte redan används.",
        ) from error

    create_session(response, db, user.id)
    return AccountSummary(
        user=UserSummary(id=user.id, email=user.email),
        companies=[MembershipSummary(company_id=company.id, company_name=company.name, role="owner")],
    )


@router.post("/login", response_model=AccountSummary)
def login(
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AccountSummary:
    email = str(body.email).lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-postadress eller lösenord stämmer inte.",
        )

    db.execute(delete(UserSession).where(UserSession.expires_at <= datetime.now(timezone.utc)))
    create_session(response, db, user.id)
    companies = [
        MembershipSummary(
            company_id=membership.company.id,
            company_name=membership.company.name,
            role=membership.role,
        )
        for membership in user.memberships
    ]
    return AccountSummary(user=UserSummary(id=user.id, email=user.email), companies=companies)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Response:
    clear_session(response, request, db)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=AccountSummary)
def current_account(
    request: Request,
    db: Session = Depends(get_db),
) -> AccountSummary:
    user = get_current_user(request, db)
    companies = [
        MembershipSummary(
            company_id=membership.company.id,
            company_name=membership.company.name,
            role=membership.role,
        )
        for membership in user.memberships
    ]
    return AccountSummary(user=UserSummary(id=user.id, email=user.email), companies=companies)


@companies_router.get("/{company_id}", response_model=MembershipSummary)
def get_company(
    company_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> MembershipSummary:
    user = get_current_user(request, db)
    membership = require_company_membership(db, user.id, company_id)
    return MembershipSummary(
        company_id=membership.company.id,
        company_name=membership.company.name,
        role=membership.role,
    )
