import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))
sys.path.insert(0, str(ROOT / "vm"))


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        env_path = Path(self.tmp.name) / "brand.env"
        env_path.write_text(
            "MAILCOW_API_KEY=test-key\nWEB_ADMIN_PASSWORD=panel-pass\n"
            "MAILCOW_API_URL=https://mail.example\nMAIL_HOSTNAME=mail.example\n"
        )
        os.environ["AZURE_MAIL_ENV"] = str(env_path)
        os.environ["AZURE_MAIL_PROVIDERS"] = str(Path(self.tmp.name) / "providers.json")
        os.environ["AZURE_MAIL_DOMAINS"] = str(Path(self.tmp.name) / "domains.json")
        os.environ["WEB_PREFIX"] = ""
        import importlib

        import app as webapp
        import lib_brand

        importlib.reload(lib_brand)
        importlib.reload(webapp)
        webapp.app.config["TESTING"] = True
        webapp.app.secret_key = "test"
        self.client = webapp.app.test_client()
        self.webapp = webapp

    def tearDown(self):
        self.tmp.cleanup()

    def test_login_then_home(self):
        bad = self.client.post("/login", data={"password": "nope"}, follow_redirects=True)
        self.assertIn(b"Wrong password", bad.data)
        ok = self.client.post("/login", data={"password": "panel-pass"}, follow_redirects=True)
        self.assertEqual(ok.status_code, 200)
        self.assertIn(b"Add a domain", ok.data)
        add = self.client.get("/add")
        self.assertIn(b"Hostinger", add.data)
        self.assertIn(b"GoDaddy", add.data)
        self.assertIn(b"I will copy the records myself", add.data)
        self.assertIn(b"MX", add.data)
        prov = self.client.get("/providers")
        self.assertIn(b"Cloudflare", prov.data)
        self.assertIn(b"Namecheap", prov.data)

    def test_dns_verify_form_uses_saved_mailbox_not_akruti(self):
        from lib_brand import save_domain

        env_path = Path(os.environ["AZURE_MAIL_ENV"])
        env_path.write_text(
            env_path.read_text()
            + "AZURE_TENANT_ID=t\nAZURE_CLIENT_ID=c\nAZURE_CLIENT_SECRET=s\nAZURE_SUBSCRIPTION_ID=sub\n"
        )
        save_domain(
            {
                "domain": "phronen.com",
                "local_part": "ruthwik",
                "email": "ruthwik@phronen.com",
            }
        )
        self.webapp.lookup_dns = lambda _e, _d: [
            {"kind": "MX", "type": "MX", "host": "@", "value": "mail.example.", "priority": 10}
        ]
        self.webapp.verification_status = lambda _e, _d: {
            "Domain": "VerificationFailed",
            "SPF": "NotStarted",
            "DKIM": "NotStarted",
            "DKIM2": "NotStarted",
        }
        self.webapp.domain_linked = lambda _e, _d: False
        self.client.post("/login", data={"password": "panel-pass"})
        page = self.client.get("/dns?domain=phronen.com")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'name="local_part"', page.data)
        self.assertIn(b"ruthwik", page.data)
        self.assertNotIn(b"akruti", page.data)
        self.assertIn(b"501 5.1.7", page.data)

    def test_templates_have_no_hardcoded_mailbox(self):
        for name in ("job.html", "dns.html"):
            html = (ROOT / "web" / "templates" / name).read_text()
            self.assertNotIn("akruti", html)


class PrefixTests(unittest.TestCase):
    def test_unauthenticated_redirect_stays_under_brands(self):
        os.environ["WEB_PREFIX"] = "/brands"
        os.environ["AZURE_MAIL_ENV"] = "/dev/null"
        os.environ["AZURE_MAIL_PROVIDERS"] = "/dev/null"
        import importlib

        import app as webapp

        importlib.reload(webapp)
        webapp.app.config["TESTING"] = True
        client = webapp.app.test_client()
        resp = client.get("/")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.headers["Location"].endswith("/brands/login"))


if __name__ == "__main__":
    unittest.main()
