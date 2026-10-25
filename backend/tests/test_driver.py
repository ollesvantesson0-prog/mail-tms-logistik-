import base64
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

DAY = "2026-10-29"  # datumet i tolkad_order


class DriverTests(unittest.TestCase):
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
        self.driver_id = self.client.post(f"{self.base}/drivers", json={"name": "Kim"}).json()["id"]
        self.vehicle_id = self.client.post(f"{self.base}/vehicles", json={"registration_number": "ABC123"}).json()["id"]

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def link(self) -> str:
        response = self.client.post(f"{self.base}/drivers/{self.driver_id}/link")
        self.assertEqual(response.status_code, 200, response.text)
        return "/api" + response.json()["path"]  # /driver/<nyckel> -> /api/driver/<nyckel>

    def assigned_order(self, driver_id: str | None = None) -> str:
        result = {"meddelandetyp": "ny_order", "ordrar": [tolkad_order("Kund AB")], "sammanfattning": ""}
        with patch("backend.app.api.orders.tolka_meddelande", return_value=result):
            order_id = self.client.post(f"{self.base}/orders/interpret", json=MESSAGE).json()["ordrar"][0]["id"]
        self.client.post(f"{self.base}/orders/{order_id}/approve")
        self.client.put(
            f"{self.base}/orders/{order_id}/assignment",
            json={"vehicle_id": self.vehicle_id, "driver_id": driver_id or self.driver_id},
        )
        return order_id

    def test_driver_sees_own_jobs_and_reports(self) -> None:
        order_id = self.assigned_order()
        other_driver = self.client.post(f"{self.base}/drivers", json={"name": "Sara"}).json()["id"]
        self.assigned_order(other_driver)
        url = self.link()

        self.client.cookies.clear()  # föraren är inte inloggad
        day = self.client.get(f"{url}?datum={DAY}").json()
        self.assertEqual(day["driver"], "Kim")
        self.assertEqual([job["id"] for job in day["jobb"]], [order_id])  # inte Saras jobb
        self.assertEqual(day["jobb"][0]["vehicle"], "ABC123")

        picked = self.client.post(f"{url}/jobs/{order_id}/events", json={"type": "picked_up"})
        self.assertEqual(picked.status_code, 201, picked.text)
        self.assertEqual(picked.json()["execution_status"], "picked_up")

        photo = base64.b64encode(b"\xff\xd8fake-jpeg").decode()
        deviation = self.client.post(
            f"{url}/jobs/{order_id}/events",
            json={"type": "deviation", "note": "En pall skadad", "photo_base64": photo, "photo_type": "image/jpeg"},
        )
        self.assertEqual(deviation.status_code, 201, deviation.text)
        self.client.post(f"{url}/jobs/{order_id}/events", json={"type": "delivered"})

        # Trafikledaren ser rapporterna och fotot.
        self.client.post("/api/auth/login", json={"email": "ett@example.com", "password": "ett-langt-testlosenord"})
        order = self.client.get(f"{self.base}/orders/{order_id}").json()
        self.assertEqual(order["execution_status"], "delivered")
        self.assertEqual([event["type"] for event in order["events"]], ["picked_up", "deviation", "delivered"])
        event = order["events"][1]
        self.assertEqual(event["driver_name"], "Kim")
        self.assertTrue(event["has_photo"])
        image = self.client.get(f"{self.base}/orders/{order_id}/events/{event['id']}/photo")
        self.assertEqual(image.content, b"\xff\xd8fake-jpeg")

    def test_rules_for_reports(self) -> None:
        order_id = self.assigned_order()
        url = self.link()
        empty = self.client.post(f"{url}/jobs/{order_id}/events", json={"type": "deviation", "note": "  "})
        self.assertEqual(empty.status_code, 400)
        bad_photo = self.client.post(
            f"{url}/jobs/{order_id}/events",
            json={"type": "deviation", "photo_base64": "inte base64!", "photo_type": "image/jpeg"},
        )
        self.assertEqual(bad_photo.status_code, 400)

        # Ett jobb som inte är förarens kan inte rapporteras.
        other_driver = self.client.post(f"{self.base}/drivers", json={"name": "Sara"}).json()["id"]
        other_order = self.assigned_order(other_driver)
        self.assertEqual(self.client.post(f"{url}/jobs/{other_order}/events", json={"type": "delivered"}).status_code, 404)

    def test_new_link_or_revoke_stops_old_link(self) -> None:
        old = self.link()
        new = self.link()
        self.assertEqual(self.client.get(old).status_code, 404)
        self.assertEqual(self.client.get(new).status_code, 200)

        self.assertEqual(self.client.delete(f"{self.base}/drivers/{self.driver_id}/link").status_code, 204)
        self.assertEqual(self.client.get(new).status_code, 404)
        self.assertEqual(self.client.get("/api/driver/pahittad").status_code, 404)

    def test_inactive_driver_link_stops_working(self) -> None:
        url = self.link()
        self.client.put(f"{self.base}/drivers/{self.driver_id}", json={"name": "Kim", "is_active": False})
        self.assertEqual(self.client.get(url).status_code, 404)


if __name__ == "__main__":
    unittest.main()
