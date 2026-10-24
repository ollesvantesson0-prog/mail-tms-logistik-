"""Password hashing and revocable browser sessions."""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, Response, status
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.entities import Membership, User, UserSession

SESSION_COOKIE = "trafikledning_session"
SESSION_MAX_AGE = 60 * 60 * 12
PASSWORD_HASHER = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return PASSWORD_HASHER.verify(password, password_hash)


def create_session(response: Response, db: Session, user_id: str) -> None:
    token = secrets.token_urlsafe(32)
    session = UserSession(
        user_id=user_id,
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=SESSION_MAX_AGE),
    )
    db.add(session)
    db.commit()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=os.getenv("APP_ENV") == "production",
        samesite="lax",
        path="/",
    )


def clear_session(response: Response, request: Request, db: Session) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        session = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
        if session is not None:
            db.delete(session)
            db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax")


def get_current_user(request: Request, db: Session) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Logga in först.")
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    session = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.expires_at > datetime.now(timezone.utc),
        )
    )
    user = db.get(User, session.user_id) if session is not None else None
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kontot är inte aktivt.")
    return user


def require_company_membership(db: Session, user_id: str, company_id: str) -> Membership:
    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.company_id == company_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Företaget hittades inte.")
    return membership
