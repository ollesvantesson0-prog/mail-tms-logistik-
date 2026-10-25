import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app
from backend.tests.test_orders import MESSAGE, tolkad_order


class PlanningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(
            bind=self.engine, autoflush=False, expire_on_commit=False
        )

        def override_get_db():
            with self.session_factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        response = self.client.post(
            "/api/auth/register",
            json={"company_name": "Åkeri", "email": "ett@example.com", "password": "ett-langt-testlosenord"},
        )
        self.base = f"/api/companies/{response.json()['companies'][0]['company_id']}"

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def approved_order(self, kyl: bool = False) -> str:
        order = tolkad_order("Kund AB")  # 4 pallar, 3200 kg, bakgavellyft, 2026-10-29
        order["krav"]["kyl"] = kyl
        result = {"meddelandetyp": "ny_order", "ordrar": [order], "sammanfattning": ""}
        with patch("backend.app.api.orders.tolka_meddelande", return_value=result):
            order_id = self.client.post(f"{self.base}/orders/interpret", json=MESSAGE).json()["ordrar"][0]["id"]
        self.client.post(f"{self.base}/orders/{order_id}/approve")
        return order_id

    def vehicle(self, **properties) -> str:
        return self.client.post(f"{self.base}/vehicles", json={"registration_number": "ABC123", **properties}).json()["id"]

    def plan(self) -> dict:
        response = self.client.get(f"{self.base}/planning?datum=2026-10-29")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_day_plan_and_warnings(self) -> None:
        order_id = self.approved_order(kyl=True)
        vehicle_id = self.vehicle(max_weight_kg=2000, pallet_places=18, has_tail_lift=True)
        self.assertEqual([order["id"] for order in self.plan()["ej_planerade"]], [order_id])

        self.client.put(f"{self.base}/orders/{order_id}/assignment", json={"vehicle_id": vehicle_id})
        plan = self.plan()
        self.assertEqual(plan["ej_planerade"], [])
        bil = plan["bilar"][0]
        self.assertEqual(bil["vikt_kg"], 3200)
        self.assertEqual(bil["pallar"], 4)
        warnings = " ".join(bil["ordrar"][0]["varningar"])
        self.assertIn("kyl", warnings)
        self.assertIn("3200 kg", warnings)
        self.assertNotIn("bakgavellyft", warnings)

        # Andra dagar påverkas inte.
        other_day = self.client.get(f"{self.base}/planning?datum=2026-10-30").json()
        self.assertEqual(other_day["bilar"][0]["ordrar"], [])

    def test_suggestion_is_checked_against_rules(self) -> None:
        order_id = self.approved_order(kyl=True)
        vehicle_id = self.vehicle()
        driver_id = self.client.post(f"{self.base}/drivers", json={"name": "Kim"}).json()["id"]
        fake = {
            "forslag": [
                {"order_id": order_id, "vehicle_id": vehicle_id, "driver_id": driver_id, "motivering": "Enda bilen."},
                {"order_id": order_id, "vehicle_id": vehicle_id, "driver_id": "", "motivering": "Dubblett."},
            ],
            "ej_planerbara": [],
            "sammanfattning": "En bil, ett jobb.",
        }
        with patch("backend.app.api.planning.foresla_plan", return_value=fake) as planner:
            response = self.client.post(f"{self.base}/planning/suggest", json={"datum": "2026-10-29"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(planner.call_args.kwargs["fordon"][0]["regnr"], "ABC123")

        forslag = response.json()["forslag"]
        self.assertEqual(len(forslag), 1)  # dubbletten tas bort
        self.assertEqual(forslag[0]["driver_id"], driver_id)
        self.assertTrue(any("kyl" in warning for warning in forslag[0]["varningar"]))

    def test_suggest_without_vehicles_or_jobs(self) -> None:
        response = self.client.post(f"{self.base}/planning/suggest", json={"datum": "2026-10-29"})
        self.assertEqual(response.json()["forslag"], [])  # inga jobb
        self.approved_order()
        response = self.client.post(f"{self.base}/planning/suggest", json={"datum": "2026-10-29"})
        self.assertEqual(response.status_code, 409)  # inga fordon


if __name__ == "__main__":
    unittest.main()
