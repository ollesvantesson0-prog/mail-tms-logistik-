import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import User, UserSession


class AuthenticationTests(unittest.TestCase):
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

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def create_account(self, company_name: str, email: str) -> dict:
        response = self.client.post(
            "/api/auth/register",
            json={
                "company_name": company_name,
                "email": email,
                "password": "ett-langt-testlosenord",
            },
        )
        self.registration_response = response
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_register_login_me_and_logout(self) -> None:
        account = self.create_account("Åkeri Ett", "ADMIN@example.com")
        self.assertEqual(account["user"]["email"], "admin@example.com")
        self.assertEqual(account["companies"][0]["company_name"], "Åkeri Ett")
        self.assertIn("httponly", self.registration_response.headers["set-cookie"].lower())

        with self.session_factory() as db:
            user = db.scalar(select(User).where(User.email == "admin@example.com"))
            self.assertIsNotNone(user)
            self.assertNotEqual(user.password_hash, "ett-langt-testlosenord")
            stored_session = db.scalar(select(UserSession).where(UserSession.user_id == user.id))
            self.assertIsNotNone(stored_session)
            self.assertNotEqual(
                stored_session.token_hash,
                self.client.cookies.get("trafikledning_session"),
            )

        me = self.client.get("/api/auth/me")
        self.assertEqual(me.status_code, 200, me.text)
        self.assertEqual(me.json()["user"]["id"], account["user"]["id"])

        self.client.post("/api/auth/logout")
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_company_membership_blocks_other_tenants(self) -> None:
        first_account = self.create_account("Åkeri Ett", "ett@example.com")
        second_account = self.create_account("Åkeri Två", "tva@example.com")
        second_company_id = second_account["companies"][0]["company_id"]

        self.client.post(
            "/api/auth/login",
            json={"email": "ett@example.com", "password": "ett-langt-testlosenord"},
        )
        allowed = self.client.get(f"/api/companies/{first_account['companies'][0]['company_id']}")
        forbidden = self.client.get(f"/api/companies/{second_company_id}")

        self.assertEqual(allowed.status_code, 200, allowed.text)
        self.assertEqual(forbidden.status_code, 404, forbidden.text)

    def test_login_rejects_wrong_password(self) -> None:
        self.create_account("Åkeri", "test@example.com")
        response = self.client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "fel-losenord"},
        )
        self.assertEqual(response.status_code, 401)

    def test_password_whitespace_is_not_changed(self) -> None:
        password = "  spaces-and-secret  "
        response = self.client.post(
            "/api/auth/register",
            json={
                "company_name": "Åkeri",
                "email": "spaces@example.com",
                "password": password,
            },
        )
        self.assertEqual(response.status_code, 201, response.text)

        trimmed_password = self.client.post(
            "/api/auth/login",
            json={"email": "spaces@example.com", "password": password.strip()},
        )
        self.assertEqual(trimmed_password.status_code, 401)

        exact_password = self.client.post(
            "/api/auth/login",
            json={"email": "spaces@example.com", "password": password},
        )
        self.assertEqual(exact_password.status_code, 200, exact_password.text)


if __name__ == "__main__":
    unittest.main()
