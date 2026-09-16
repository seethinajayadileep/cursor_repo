"""Parse public tunnel URLs from cloudflared / ngrok logs."""

from __future__ import annotations

import unittest

from cursor_pocket.tunnel import parse_public_url


class TunnelParseTests(unittest.TestCase):
    def test_cloudflare_quick_tunnel(self) -> None:
        log = (
            "INF |  Your quick Tunnel has been created! Visit it at:\n"
            "INF |  https://random-words-here.trycloudflare.com                     |\n"
        )
        self.assertEqual(parse_public_url(log), "https://random-words-here.trycloudflare.com")

    def test_ngrok_free(self) -> None:
        log = "Forwarding  https://abc123.ngrok-free.app -> http://localhost:8787"
        self.assertEqual(parse_public_url(log), "https://abc123.ngrok-free.app")

    def test_ignores_noise(self) -> None:
        self.assertIsNone(parse_public_url("starting tunnel, please wait"))


if __name__ == "__main__":
    unittest.main()
