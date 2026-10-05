import sys
import unittest
from pathlib import Path

from flask import Flask, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web"))
from security import admin_password, csrf_ok, csrf_token, password_ok, same_origin  # noqa: E402


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


class OriginTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = "test"

    def test_null_origin_uses_referer(self):
        with self.app.test_request_context(
            "/add",
            method="POST",
            headers={
                "Host": "mail.example",
                "Origin": "null",
                "Referer": "https://mail.example/brands/add",
            },
        ):
            self.assertTrue(same_origin(request))

    def test_null_origin_without_referer_is_rejected(self):
        with self.app.test_request_context(
            "/add",
            method="POST",
            headers={"Host": "mail.example", "Origin": "null"},
        ):
            self.assertFalse(same_origin(request))

    def test_matching_origin_ok(self):
        with self.app.test_request_context(
            "/add",
            method="POST",
            headers={"Host": "mail.example", "Origin": "https://mail.example"},
        ):
            self.assertTrue(same_origin(request))

    def test_csrf_token_roundtrip(self):
        with self.app.test_request_context("/add", method="POST", data={"csrf": "fixed-token"}):
            from flask import session

            session["csrf"] = "fixed-token"
            self.assertTrue(csrf_ok(request))
            session["csrf"] = "other"
            self.assertFalse(csrf_ok(request))


if __name__ == "__main__":
    unittest.main()
