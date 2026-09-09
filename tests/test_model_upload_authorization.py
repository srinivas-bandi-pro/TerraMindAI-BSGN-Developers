"""Authorization tests for the restricted model upload workflow."""

import unittest

from app import create_app
from app.models.database import db
from app.models.user import User


class ModelUploadAuthorizationTests(unittest.TestCase):
    """Verify access to model uploads is limited to authenticated admins."""

    def setUp(self) -> None:
        self.app = create_app("testing")
        self.app.config["MODEL_UPLOAD_ENABLED"] = True
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            self.user = self._create_user("user@example.com", "user")
            self.admin = self._create_user("admin@example.com", "admin")
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @staticmethod
    def _create_user(email: str, role: str) -> User:
        user = User(name=role.title(), email=email, role=role)
        user.set_password("test-password")
        db.session.add(user)
        db.session.commit()
        return user

    def _sign_in(self, user: User) -> None:
        with self.client.session_transaction() as session:
            session["_user_id"] = str(user.id)
            session["_fresh"] = True

    def test_anonymous_user_is_redirected_to_login(self) -> None:
        response = self.client.get("/model-upload")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login?next=%2Fmodel-upload", response.headers["Location"])

    def test_non_admin_receives_friendly_access_denied_page(self) -> None:
        self._sign_in(self.user)

        response = self.client.get("/model-upload")

        self.assertEqual(response.status_code, 403)
        self.assertIn("text/html", response.content_type)
        self.assertIn("Access denied", response.get_data(as_text=True))

    def test_admin_can_open_model_upload_page(self) -> None:
        self._sign_in(self.admin)

        response = self.client.get("/model-upload")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Upload trained model", response.get_data(as_text=True))

    def test_non_admin_api_request_returns_api_error(self) -> None:
        self._sign_in(self.user)

        response = self.client.post("/api/model/upload")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"]["code"], "forbidden")


if __name__ == "__main__":
    unittest.main()
