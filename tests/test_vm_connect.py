"""Reach Pocket from another address, like a second VM — no internet tunnel."""

from __future__ import annotations

import json
import socket
import urllib.request
import unittest

from cursor_pocket.auth import Auth
from cursor_pocket.jobs import JobStore
from cursor_pocket.net import guest_host_url, lan_ipv4_addresses
from cursor_pocket.runner import Runner
from cursor_pocket.server import PocketState, serve


class TwoMachineConnectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = PocketState(
            auth=Auth.generate("123456"),
            store=JobStore(),
            runner=Runner(demo=True),
            workspaces=[{"name": "workspace", "path": "/tmp"}],
            host="0.0.0.0",
            port=0,
            laptop_name="vm-host",
        )
        self.httpd = serve(self.state, "0.0.0.0", 0)
        self.port = self.httpd.server_address[1]

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def _json(self, base: str, method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode())

    def test_pair_from_every_local_ip_without_a_tunnel(self) -> None:
        ips = ["127.0.0.1", *lan_ipv4_addresses()]
        seen: set[str] = set()
        reached = 0
        for ip in ips:
            if ip in seen:
                continue
            seen.add(ip)
            try:
                socket.create_connection((ip, self.port), timeout=2).close()
            except OSError:
                continue
            base = f"http://{ip}:{self.port}"
            health = self._json(base, "GET", "/api/health")
            self.assertTrue(health["ok"])
            self.assertFalse(health["internet_required"])
            self.assertEqual(health["vm_url"], guest_host_url(self.port))
            paired = self._json(base, "POST", "/api/pair", {"pin": "123456"})
            self.assertTrue(paired["token"])
            reached += 1
        self.assertGreaterEqual(reached, 1)
        self.assertEqual(guest_host_url(self.port), f"http://10.0.2.2:{self.port}")


if __name__ == "__main__":
    unittest.main()
