"""LAN URL helpers."""

from __future__ import annotations

import unittest

from cursor_pocket.net import _usable, public_base_urls


class NetTests(unittest.TestCase):
    def test_public_urls_include_localhost_when_bound_all(self) -> None:
        urls = public_base_urls("0.0.0.0", 8787)
        self.assertIn("http://127.0.0.1:8787", urls)

    def test_skips_loopback_and_docker_bridges(self) -> None:
        self.assertFalse(_usable("127.0.0.1"))
        self.assertFalse(_usable("172.17.0.2"))
        self.assertTrue(_usable("192.168.1.20"))


if __name__ == "__main__":
    unittest.main()
