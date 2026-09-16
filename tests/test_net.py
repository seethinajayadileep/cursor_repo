"""LAN / VM URL helpers. Internet is not required."""

from __future__ import annotations

import unittest

from cursor_pocket.net import (
    address_kind,
    connection_routes,
    format_connect_help,
    guest_host_url,
    public_base_urls,
    _usable,
)


class NetTests(unittest.TestCase):
    def test_public_urls_include_localhost_when_bound_all(self) -> None:
        urls = public_base_urls("0.0.0.0", 8787)
        self.assertIn("http://127.0.0.1:8787", urls)

    def test_skips_loopback_keeps_lan_and_vm_bridges(self) -> None:
        self.assertFalse(_usable("127.0.0.1"))
        self.assertFalse(_usable("10.0.2.2"))
        self.assertEqual(address_kind("172.17.0.2"), "vm")
        self.assertTrue(_usable("172.17.0.2"))
        self.assertEqual(address_kind("192.168.1.20"), "lan")
        self.assertTrue(_usable("192.168.1.20"))
        self.assertEqual(address_kind("100.64.1.8"), "lan")

    def test_guest_url_is_qemu_android_gateway(self) -> None:
        self.assertEqual(guest_host_url(8787), "http://10.0.2.2:8787")

    def test_routes_cover_two_vms_without_internet(self) -> None:
        routes = connection_routes("0.0.0.0", 8799)
        kinds = [item["kind"] for item in routes]
        self.assertIn("emulator", kinds)
        self.assertIn("usb", kinds)
        self.assertNotIn("internet", kinds)
        emu = next(item for item in routes if item["kind"] == "emulator")
        self.assertEqual(emu["url"], "http://10.0.2.2:8799")
        help_text = format_connect_help("127.0.0.1", 8787)
        self.assertIn("NOT required", help_text)
        self.assertIn("10.0.2.2", help_text)
        self.assertIn("--online", help_text)
        self.assertNotIn("trycloudflare", help_text)

    def test_online_url_is_optional_last_route(self) -> None:
        routes = connection_routes("127.0.0.1", 8787, "https://demo.trycloudflare.com")
        self.assertEqual(routes[-1]["kind"], "internet")
        self.assertEqual(routes[-1]["url"], "https://demo.trycloudflare.com")
        help_text = format_connect_help("127.0.0.1", 8787, "https://demo.trycloudflare.com")
        self.assertIn("trycloudflare", help_text)
        self.assertIn("10.0.2.2", help_text)


if __name__ == "__main__":
    unittest.main()
