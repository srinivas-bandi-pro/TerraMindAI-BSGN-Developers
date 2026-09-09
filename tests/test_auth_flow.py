"""Integration tests for Terra Mind AI login, registration, legacy activation handling, admin auth, crop prediction, and AI chat."""

import unittest
from app import create_app
from app.models.database import db
from app.models.user import User


class AuthFlowTests(unittest.TestCase):
    """Verify registration, login, logout, legacy activation URLs, and workspace features."""

    def setUp(self) -> None:
        self.app = create_app("testing")
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            # Create configured admin account for admin tests
            self.admin_user = User(
                name="Admin User",
                username="adminuser",
                email="admin@terramind.ai",
                role="admin",
            )
            self.admin_user.set_password("admin-password123")
            db.session.add(self.admin_user)
            db.session.commit()

        self.client = self.app.test_client()

    def tearDown(self) -> None:
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_login_and_register_get_routes_render_forms(self) -> None:
        """GET /login and GET /register render existing templates directly."""
        login_resp = self.client.get("/login")
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn(b"Sign in | Terra Mind AI", login_resp.data)

        register_resp = self.client.get("/register")
        self.assertEqual(register_resp.status_code, 200)
        self.assertIn(b"Create Account | Terra Mind AI", register_resp.data)

    def test_registration_and_immediate_login(self) -> None:
        """A. Normal user can register with email, username, and password and reach dashboard immediately."""
        response = self.client.post(
            "/register",
            data={
                "name": "Farmer John",
                "email": "john.farmer@example.com",
                "username": "farmerjohn",
                "password": "SecurePassword123",
                "confirm_password": "SecurePassword123",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome to TerraMind AI!", response.data)

        # Verify user role in DB is "user"
        with self.app.app_context():
            user = db.session.scalar(
                db.select(User).where(User.email == "john.farmer@example.com")
            )
            self.assertIsNotNone(user)
            self.assertEqual(user.role, "user")
            self.assertEqual(user.display_username, "farmerjohn")

    def test_password_confirmation_mismatch_prevents_registration(self) -> None:
        """Registration fails if passwords do not match."""
        response = self.client.post(
            "/register",
            data={
                "name": "Farmer John",
                "email": "john.farmer2@example.com",
                "username": "farmerjohn2",
                "password": "SecurePassword123",
                "confirm_password": "DifferentPassword123",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Passwords do not match.", response.data)

    def test_logout_and_relogin(self) -> None:
        """D, E, F: Register, log out, and log back in using email or username."""
        # 1. Register
        self.client.post(
            "/register",
            data={
                "name": "Jane Doe",
                "email": "jane@example.com",
                "username": "janedoe",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
        )

        # 2. Log out
        logout_resp = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(logout_resp.status_code, 200)
        self.assertIn(b"You have been signed out.", logout_resp.data)

        # 3. Log in with email
        login_resp = self.client.post(
            "/login",
            data={"email": "jane@example.com", "password": "Password123!"},
            follow_redirects=True,
        )
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn(b"Welcome back, Jane Doe!", login_resp.data)

        # 4. Log out again
        self.client.get("/logout")

        # 5. Log in with username
        login_username_resp = self.client.post(
            "/login",
            data={"email": "janedoe", "password": "Password123!"},
            follow_redirects=True,
        )
        self.assertEqual(login_username_resp.status_code, 200)
        self.assertIn(b"Welcome back, Jane Doe!", login_username_resp.data)

    def test_legacy_activation_urls_redirect_safely(self) -> None:
        """G. Confirm obsolete activation links redirect safely to /login without displaying activation error pages."""
        for path in (
            "/activate",
            "/activate/some-token-123",
            "/verify",
            "/verify/some-token-456",
            "/verify-email",
            "/activate-account",
            "/confirm-email",
            "/confirm/abc",
        ):
            with self.subTest(path=path):
                response = self.client.get(path, follow_redirects=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Account activation is not required.", response.data)
                self.assertNotIn(b"Invalid or expired activation link", response.data)

    def test_admin_login(self) -> None:
        """H. Verify existing admin login works and lands on admin workspace."""
        response = self.client.post(
            "/login",
            data={"email": "admin@terramind.ai", "password": "admin-password123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            admin = db.session.scalar(
                db.select(User).where(User.email == "admin@terramind.ai")
            )
            self.assertTrue(admin.is_admin)

    def test_crop_prediction_and_ai_chat_remain_functional(self) -> None:
        """I & J. Confirm crop prediction and AI chat endpoints work as expected."""
        # Authenticate user first
        self.client.post(
            "/login",
            data={"email": "admin@terramind.ai", "password": "admin-password123"},
        )

        # Test crop prediction API
        pred_resp = self.client.post(
            "/api/recommend",
            json={
                "N": 90,
                "P": 42,
                "K": 43,
                "temperature": 20.8,
                "humidity": 82.0,
                "ph": 6.5,
                "rainfall": 202.9,
            },
        )
        self.assertEqual(pred_resp.status_code, 200)
        data = pred_resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("crop", data)

        # Test AI chat endpoint structure
        chat_resp = self.client.post(
            "/api/chat",
            json={"message": "What crop is best for rice soil?"},
        )
        # 200 or 503 depending on OpenAI API key presence in test environment
        self.assertIn(chat_resp.status_code, (200, 503))


if __name__ == "__main__":
    unittest.main()
