import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app


def tolkad_order(kund: str) -> dict:
    return {
        "kund": {"foretag": kund, "kontaktperson": "", "telefon": "", "epost": ""},
        "kundreferens": "BB-2291",
        "upphamtning": {
            "foretag": kund, "adress": "", "postnummer": "", "ort": "Sävedalen",
            "datum": "2026-10-29", "tid_fran": "07:00", "tid_till": "09:00",
        },
        "leveranser": [{
            "foretag": "", "adress": "", "postnummer": "", "ort": "Mölndal",
            "datum": "2026-10-29", "tid_fran": "", "tid_till": "12:00",
        }],
        "gods": [{"antal": 4, "typ": "EUR-pall", "beskrivning": "gips", "vikt_kg": 3200, "matt": ""}],
        "krav": {
            "bakgavellyft": True, "kran": False, "kyl": False, "temperatur": "", "adr": False,
            "un_nummer": "", "barhjalp": False, "akut": False, "aterkommande": False,
        },
        "galler_order": "",
        "saknas": [],
        "osakerheter": [],
    }


FAKE_RESULT = {
    "meddelandetyp": "ny_order",
    "ordrar": [tolkad_order("Bergqvists Bygg AB"), tolkad_order("Bergqvists Bygg AB")],
    "sammanfattning": "Två transporter av gipsskivor.",
}

MESSAGE = {
    "meddelande": "Hej! Vi behöver en transport på torsdag.",
    "avsandare": "linda.ek@bergqvistsbygg.se",
    "mottagen": "2026-10-27T07:45:00",
}


class OrderTests(unittest.TestCase):
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
        self.company_id = self.create_account("Åkeri Ett", "ett@example.com")

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def create_account(self, company_name: str, email: str) -> str:
        response = self.client.post(
            "/api/auth/register",
            json={"company_name": company_name, "email": email, "password": "ett-langt-testlosenord"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["companies"][0]["company_id"]

    def interpret(self, result: dict = FAKE_RESULT) -> dict:
        with patch("backend.app.api.orders.tolka_meddelande", return_value=result) as fake:
            response = self.client.post(f"/api/companies/{self.company_id}/orders/interpret", json=MESSAGE)
        self.assertEqual(response.status_code, 201, response.text)
        fake.assert_called_once()
        return response.json()

    def test_interpret_creates_one_pending_order_per_interpreted_order(self) -> None:
        result = self.interpret()
        self.assertEqual(result["meddelandetyp"], "ny_order")
        self.assertEqual(len(result["ordrar"]), 2)
        self.assertTrue(all(order["status"] == "pending" for order in result["ordrar"]))
        self.assertEqual(result["ordrar"][0]["meddelande"]["avsandare"], MESSAGE["avsandare"])

        pending = self.client.get(f"/api/companies/{self.company_id}/orders?status=pending")
        self.assertEqual(len(pending.json()), 2)

    def test_non_order_message_creates_no_orders(self) -> None:
        result = self.interpret({"meddelandetyp": "ej_order", "ordrar": [], "sammanfattning": "Fakturafråga."})
        self.assertEqual(result["ordrar"], [])
        self.assertEqual(self.client.get(f"/api/companies/{self.company_id}/orders").json(), [])

    def test_edit_approve_and_export(self) -> None:
        order_id = self.interpret()["ordrar"][0]["id"]
        url = f"/api/companies/{self.company_id}/orders/{order_id}"

        edited = tolkad_order("Rättat Företag AB")
        response = self.client.put(url, json={"order": edited})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["order"]["kund"]["foretag"], "Rättat Företag AB")

        approved = self.client.post(f"{url}/approve")
        self.assertEqual(approved.json()["status"], "approved")

        # En granskad order är låst.
        self.assertEqual(self.client.put(url, json={"order": edited}).status_code, 409)
        self.assertEqual(self.client.post(f"{url}/discard").status_code, 409)

        export = self.client.get(f"/api/companies/{self.company_id}/orders/export.csv")
        self.assertEqual(export.status_code, 200)
        lines = export.text.lstrip("﻿").strip().splitlines()
        self.assertEqual(len(lines), 2)  # rubrikrad + den godkända ordern
        self.assertIn("Rättat Företag AB", lines[1])
        self.assertIn("4 EUR-pall gips", lines[1])

    def test_discard(self) -> None:
        order_id = self.interpret()["ordrar"][0]["id"]
        response = self.client.post(f"/api/companies/{self.company_id}/orders/{order_id}/discard")
        self.assertEqual(response.json()["status"], "discarded")

    def test_other_company_cannot_see_or_change_orders(self) -> None:
        order_id = self.interpret()["ordrar"][0]["id"]
        own_company_id = self.company_id
        self.company_id = self.create_account("Åkeri Två", "tva@example.com")  # loggar in som tvåan

        base = f"/api/companies/{own_company_id}/orders"
        self.assertEqual(self.client.get(base).status_code, 404)
        self.assertEqual(self.client.get(f"{base}/{order_id}").status_code, 404)
        self.assertEqual(self.client.post(f"{base}/{order_id}/approve").status_code, 404)

        # Inte heller via det egna företagets adress.
        other = f"/api/companies/{self.company_id}/orders/{order_id}"
        self.assertEqual(self.client.get(other).status_code, 404)

    def test_requires_login(self) -> None:
        self.client.post("/api/auth/logout")
        response = self.client.post(f"/api/companies/{self.company_id}/orders/interpret", json=MESSAGE)
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
