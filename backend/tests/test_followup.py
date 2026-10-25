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

# tolkad_order: hämtas 2026-10-29 07:00–09:00, levereras senast 12:00.
LOGIN = {"email": "ett@example.com", "password": "ett-langt-testlosenord"}


class FollowupTests(unittest.TestCase):
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
        response = self.client.post("/api/auth/register", json={"company_name": "Åkeri", **LOGIN})
        self.base = f"/api/companies/{response.json()['companies'][0]['company_id']}"
        self.driver_id = self.client.post(f"{self.base}/drivers", json={"name": "Kim"}).json()["id"]
        self.vehicle_id = self.client.post(f"{self.base}/vehicles", json={"registration_number": "ABC123"}).json()["id"]
        path = self.client.post(f"{self.base}/drivers/{self.driver_id}/link").json()["path"]
        self.driver_url = f"/api{path}"

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def approved_order(self, assign: bool = True) -> str:
        result = {"meddelandetyp": "ny_order", "ordrar": [tolkad_order("Kund AB")], "sammanfattning": ""}
        with patch("backend.app.api.orders.tolka_meddelande", return_value=result):
            order_id = self.client.post(f"{self.base}/orders/interpret", json=MESSAGE).json()["ordrar"][0]["id"]
        self.client.post(f"{self.base}/orders/{order_id}/approve")
        if assign:
            self.client.put(
                f"{self.base}/orders/{order_id}/assignment",
                json={"vehicle_id": self.vehicle_id, "driver_id": self.driver_id},
            )
        return order_id

    def followup(self, nu: str) -> dict:
        response = self.client.get(f"{self.base}/followup?nu={nu}")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def types(self, nu: str) -> list[str]:
        return sorted(item["typ"] for item in self.followup(nu)["items"])

    def report(self, order_id: str, body: dict) -> dict:
        response = self.client.post(f"{self.driver_url}/jobs/{order_id}/events", json=body)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_late_jobs_follow_the_time_windows(self) -> None:
        order_id = self.approved_order()
        self.approved_order(assign=False)
        self.assertEqual(self.types("2026-10-29T08:00"), ["ej_planerad"])
        self.assertEqual(self.types("2026-10-29T09:30"), ["ej_planerad", "sen_upphamtning"])

        self.report(order_id, {"type": "picked_up"})
        self.assertEqual(self.types("2026-10-29T12:30"), ["ej_planerad", "sen_leverans"])
        self.report(order_id, {"type": "delivered"})
        self.assertEqual(self.types("2026-10-29T12:30"), ["ej_planerad"])

        # Andra dagar räknas inte som sena.
        self.assertEqual(self.types("2026-10-30T12:30"), [])

        self.assertEqual([order["id"] for order in self.followup("2026-10-29T12:30")["levererade"]], [order_id])
        summary = self.followup("2026-10-29T12:30")["idag"]
        self.assertEqual((summary["jobb"], summary["levererade"], summary["ej_paborjade"]), (2, 1, 1))

    def test_deviation_stays_until_handled(self) -> None:
        order_id = self.approved_order()
        self.report(order_id, {"type": "deviation", "note": "Skadad pall"})
        self.report(order_id, {"type": "delay", "note": "ca 30 min, kö"})
        delay_without_note = self.client.post(f"{self.driver_url}/jobs/{order_id}/events", json={"type": "delay"})
        self.assertEqual(delay_without_note.status_code, 400)

        items = self.followup("2026-10-30T08:00")["items"]  # syns även andra dagar
        self.assertEqual([item["typ"] for item in items], ["avvikelse", "forsening"])  # allvarligast först
        self.assertIn("Kim: Skadad pall", items[0]["text"])

        handled = self.client.post(f"{self.base}/orders/{order_id}/events/{items[0]['event_id']}/handle")
        self.assertEqual(handled.status_code, 200, handled.text)
        self.assertEqual(self.types("2026-10-30T08:00"), ["forsening"])

    def test_notice_draft_uses_swedish_time_and_customer_contact(self) -> None:
        order_id = self.approved_order()
        job = self.report(order_id, {"type": "delivered"})
        event_id = job["events"][0]["id"]
        draft = {"amne": "Levererat", "text": "Er leverans är framme."}
        with patch("backend.app.api.orders.skriv_kundbesked", return_value=draft) as fake:
            response = self.client.post(f"{self.base}/orders/{order_id}/notice-draft", json={"event_id": event_id})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["epost"], MESSAGE["avsandare"])
        handelse = fake.call_args.kwargs["handelse"]
        self.assertEqual(handelse["typ"], "delivered")
        self.assertRegex(handelse["tid"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")

        with patch("backend.app.api.orders.skriv_kundbesked", return_value=draft):
            computed = self.client.post(f"{self.base}/orders/{order_id}/notice-draft", json={"typ": "delay"})
        self.assertEqual(computed.status_code, 200, computed.text)
        self.assertEqual(self.client.post(f"{self.base}/orders/{order_id}/notice-draft", json={}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
