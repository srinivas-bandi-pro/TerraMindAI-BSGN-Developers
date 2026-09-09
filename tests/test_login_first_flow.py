"""Integration tests for the login-first workspace flow."""

import unittest

from app import create_app
from app.models.database import db
from app.models.user import User


class LoginFirstFlowTests(unittest.TestCase):
    """Verify anonymous visitors cannot reach workspace pages."""

    def setUp(self) -> None:
        self.app = create_app("testing")
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            self.user = User(name="Test User", username="testuser", email="user@example.com")
            self.user.set_password("test-password")
            db.session.add(self.user)
            db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_anonymous_workspace_routes_redirect_to_login(self) -> None:
        for path in ("/dashboard", "/predict", "/prediction", "/history", "/analytics", "/model-upload", "/profile"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/login?next=", response.headers["Location"])

    def test_login_sends_user_to_dashboard(self) -> None:
        response = self.client.post(
            "/login",
            data={"email": "user@example.com", "password": "test-password"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/dashboard"))


if __name__ == "__main__":
    unittest.main()
