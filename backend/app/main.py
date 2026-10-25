"""FastAPI entry point for the traffic management platform."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.app.api.auth import companies_router, router as auth_router
from backend.app.api.driver import router as driver_router
from backend.app.api.fleet import router as fleet_router
from backend.app.api.followup import router as followup_router
from backend.app.api.orders import router as orders_router
from backend.app.api.planning import router as planning_router
from backend.app.db.session import engine

app = FastAPI(title="AI Trafikledning API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)
app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(orders_router)
app.include_router(fleet_router)
app.include_router(planning_router)
app.include_router(driver_router)
app.include_router(followup_router)


@app.get("/api/health", tags=["system"])
def health_check() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
