"""Static contracts for the browser-side form validation implementation."""

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FrontendValidationTests(unittest.TestCase):
    """Keep required form accessibility and validation hooks from regressing."""

    def test_prediction_form_has_native_validation_boundaries(self) -> None:
        """Prediction inputs expose required ranges for browser-side validation."""
        template = (PROJECT_ROOT / "templates" / "predict.html").read_text(
            encoding="utf-8"
        )

        for field in ("nitrogen", "phosphorus", "potassium", "humidity", "rainfall"):
            with self.subTest(field=field):
                self.assertIn(f'id="{field}"', template)
        self.assertIn('aria-describedby="nitrogen-hint nitrogen-error"', template)
        self.assertIn('max="500"', template)

    def test_contact_form_validation_has_accessible_feedback(self) -> None:
        """Contact validation retains inline errors, counter, reset, and toast flow."""
        template = (PROJECT_ROOT / "templates" / "contact.html").read_text(
            encoding="utf-8"
        )
        script = (PROJECT_ROOT / "static" / "js" / "contact.js").read_text(
            encoding="utf-8"
        )

        self.assertIn('id="contact-form"', template)
        self.assertIn('aria-live="polite"', template)
        self.assertIn('id="contact-message-count"', template)
        self.assertIn("Enter a valid email address.", script)
        self.assertIn("AgriSmartToast.show", script)
        self.assertIn("form.addEventListener('reset'", script)
