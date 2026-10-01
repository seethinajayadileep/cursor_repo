import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web"))
from security import admin_password, password_ok  # noqa: E402


class PasswordTests(unittest.TestCase):
    def test_only_admin_password_counts(self):
        self.assertEqual(admin_password({"WEB_ADMIN_PASSWORD": "secret", "MAILCOW_API_KEY": "api"}), "secret")
        self.assertEqual(admin_password({"MAILCOW_API_KEY": "api"}), "")

    def test_compare_rejects_wrong_and_empty(self):
        self.assertTrue(password_ok("secret", "secret"))
        self.assertFalse(password_ok("secret", "other"))
        self.assertFalse(password_ok("secret", ""))
        self.assertFalse(password_ok("", "secret"))
        self.assertFalse(password_ok("api-key", "secret"))


if __name__ == "__main__":
    unittest.main()
