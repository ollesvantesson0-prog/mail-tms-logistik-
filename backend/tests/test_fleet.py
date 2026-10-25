import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app


class FleetTests(unittest.TestCase):
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

    def url(self, rest: str) -> str:
        return f"/api/companies/{self.company_id}{rest}"

    def test_create_list_and_update_vehicle(self) -> None:
        created = self.client.post(self.url("/vehicles"), json={"registration_number": "abc 123", "description": "Kylbil"})
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["registration_number"], "ABC123")

        vehicle_id = created.json()["id"]
        updated = self.client.put(
            self.url(f"/vehicles/{vehicle_id}"),
            json={"registration_number": "ABC123", "description": "Kylbil med bakgavellyft", "is_active": False},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertFalse(updated.json()["is_active"])

        vehicles = self.client.get(self.url("/vehicles")).json()
        self.assertEqual([vehicle["description"] for vehicle in vehicles], ["Kylbil med bakgavellyft"])

    def test_duplicate_registration_number_is_rejected(self) -> None:
        self.client.post(self.url("/vehicles"), json={"registration_number": "ABC123"})
        duplicate = self.client.post(self.url("/vehicles"), json={"registration_number": "abc-123"})
        self.assertEqual(duplicate.status_code, 409)
        self.assertIn("ABC123", duplicate.json()["detail"])

        # Ett annat åkeri får ha en bil med samma nummer i sin egen flotta.
        self.company_id = self.create_account("Åkeri Två", "tva@example.com")
        self.assertEqual(self.client.post(self.url("/vehicles"), json={"registration_number": "ABC123"}).status_code, 201)

    def test_create_and_update_driver(self) -> None:
        created = self.client.post(self.url("/drivers"), json={"name": " Kim Berg ", "phone": "070-111 22 33"})
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["name"], "Kim Berg")

        driver_id = created.json()["id"]
        updated = self.client.put(self.url(f"/drivers/{driver_id}"), json={"name": "Kim Berg", "is_active": False})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertFalse(updated.json()["is_active"])
        self.assertEqual(len(self.client.get(self.url("/drivers")).json()), 1)

    def test_other_company_cannot_see_or_change_fleet(self) -> None:
        vehicle_id = self.client.post(self.url("/vehicles"), json={"registration_number": "ABC123"}).json()["id"]
        driver_id = self.client.post(self.url("/drivers"), json={"name": "Kim"}).json()["id"]
        own_company_id = self.company_id

        self.company_id = self.create_account("Åkeri Två", "tva@example.com")  # loggar in som tvåan
        self.assertEqual(self.client.get(f"/api/companies/{own_company_id}/vehicles").status_code, 404)
        self.assertEqual(self.client.get(f"/api/companies/{own_company_id}/drivers").status_code, 404)
        self.assertEqual(
            self.client.put(self.url(f"/vehicles/{vehicle_id}"), json={"registration_number": "XYZ999"}).status_code,
            404,
        )
        self.assertEqual(self.client.put(self.url(f"/drivers/{driver_id}"), json={"name": "Kapad"}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
