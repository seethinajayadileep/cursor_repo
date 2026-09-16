"""Auth pairing and lockout."""

from __future__ import annotations

import unittest

from cursor_pocket.auth import Auth, AuthError, extract_bearer


class AuthTests(unittest.TestCase):
    def test_pair_and_check(self) -> None:
        auth = Auth.generate("123456")
        token = auth.pair("123456")
        auth.check(token)

    def test_wrong_pin_length_does_not_crash(self) -> None:
        auth = Auth.generate("123456")
        with self.assertRaises(AuthError):
            auth.pair("12")

    def test_lockout(self) -> None:
        auth = Auth.generate("123456")
        auth.max_attempts = 2
        with self.assertRaises(AuthError):
            auth.pair("000000")
        with self.assertRaises(AuthError) as ctx:
            auth.pair("000000")
        self.assertEqual(ctx.exception.status, 423)
        with self.assertRaises(AuthError):
            auth.pair("123456")

    def test_extract_bearer(self) -> None:
        self.assertEqual(extract_bearer("Bearer abc", None), "abc")
        self.assertEqual(extract_bearer(None, "xyz"), "xyz")
        self.assertIsNone(extract_bearer("Token abc", None))


if __name__ == "__main__":
    unittest.main()
