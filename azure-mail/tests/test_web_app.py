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
        os.environ["WEB_COOKIE_SECURE"] = "0"
        os.environ["WEB_LOGIN_FAIL_LIMIT"] = "20"
        import importlib

        import app as webapp
        import lib_brand
        import security

        importlib.reload(lib_brand)
        importlib.reload(security)
        importlib.reload(webapp)
        webapp.app.config["TESTING"] = True
        webapp.app.secret_key = "test"
        self.client = webapp.app.test_client()
        self.webapp = webapp

    def tearDown(self):
        self.tmp.cleanup()

    def test_login_then_home(self):
        bad = self.client.post("/login", data={"password": "nope"}, follow_redirects=True)
        self.assertIn(b"Wrong admin password", bad.data)
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

    def test_central_mail_lists_domains_and_mailboxes(self):
        self.webapp.mail_directory = lambda _e: {
            "domains": [
                {
                    "domain": "phronen.com",
                    "active": True,
                    "source": "mailcow",
                    "send_ready": True,
                    "saved": {},
                    "mailboxes": [
                        {
                            "email": "ruthwik@phronen.com",
                            "local_part": "ruthwik",
                            "domain": "phronen.com",
                            "name": "ruthwik",
                            "active": True,
                        }
                    ],
                }
            ],
            "domain_count": 1,
            "mailbox_count": 1,
            "error": None,
            "webmail": "https://mail.example/",
        }
        self.client.post("/login", data={"password": "panel-pass"})
        page = self.client.get("/mailboxes")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Central mail", page.data)
        self.assertIn(b"phronen.com", page.data)
        self.assertIn(b"ruthwik@phronen.com", page.data)
        self.assertIn(b"Send ready", page.data)
        self.assertIn(b"/mailboxes/webmail", page.data)
        self.assertIn(b"email=ruthwik", page.data)
        found = self.client.get("/mailboxes?q=ruthwik")
        self.assertIn(b"ruthwik@phronen.com", found.data)
        missing = self.client.get("/mailboxes?q=no-such-box")
        self.assertIn(b"No mailboxes yet", missing.data)

    def test_webmail_sso_requires_admin_and_known_mailbox(self):
        anon = self.client.get("/mailboxes/webmail?email=ruthwik@phronen.com")
        self.assertEqual(anon.status_code, 302)
        self.assertIn("/login", anon.headers["Location"])
        self.client.post("/login", data={"password": "panel-pass"})
        unknown = self.client.get("/mailboxes/webmail?email=nobody@phronen.com", follow_redirects=True)
        self.assertIn(b"not a mailbox", unknown.data)
        self.webapp.mailbox_known = lambda _e, email: email == "ruthwik@phronen.com"
        self.webapp.persist_sso_secret = lambda _e=None: "s" * 32
        self.webapp.webmail_sso_url = (
            lambda _e, email: f"https://mail.example/mailbox-sso.php?u={email}&t=ticket"
        )
        opened = self.client.get("/mailboxes/webmail?email=ruthwik@phronen.com")
        self.assertEqual(opened.status_code, 302)
        self.assertIn("mailbox-sso.php", opened.headers["Location"])
        self.assertIn("ruthwik@phronen.com", opened.headers["Location"])


    def test_mailboxes_requires_admin_session(self):
        anon = self.client.get("/mailboxes")
        self.assertEqual(anon.status_code, 302)
        self.assertIn("/login", anon.headers["Location"])
        job = self.client.get("/job/x.json")
        self.assertEqual(job.status_code, 401)

    def test_api_key_and_mailbox_password_cannot_open_panel(self):
        for secret in ("test-key", "ruthwik-mailbox", ""):
            denied = self.client.post("/login", data={"password": secret}, follow_redirects=True)
            self.assertIn(b"Wrong admin password", denied.data)
            home = self.client.get("/")
            self.assertEqual(home.status_code, 302)
            self.assertIn("/login", home.headers["Location"])


class CsrfAddTests(unittest.TestCase):
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
        os.environ["WEB_COOKIE_SECURE"] = "0"
        os.environ["WEB_LOGIN_FAIL_LIMIT"] = "20"
        import importlib

        import app as webapp
        import lib_brand
        import security

        importlib.reload(lib_brand)
        importlib.reload(security)
        importlib.reload(webapp)
        webapp.app.config["TESTING"] = False
        webapp.app.secret_key = "test"
        self.client = webapp.app.test_client()
        self.webapp = webapp

    def tearDown(self):
        self.tmp.cleanup()

    def _login(self):
        return self.client.post(
            "/login",
            data={"password": "panel-pass"},
            headers={"Origin": "http://localhost"},
            follow_redirects=True,
        )

    def test_add_form_includes_csrf(self):
        self._login()
        page = self.client.get("/add")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'name="csrf"', page.data)

    def test_add_post_origin_null_without_csrf_is_blocked(self):
        self._login()
        blocked = self.client.post(
            "/add",
            data={"domain": "blocked.example", "local_part": "hi", "provider": "manual"},
            headers={"Origin": "null"},
        )
        self.assertEqual(blocked.status_code, 302)
        self.assertIn("/add", blocked.headers["Location"])
        follow = self.client.get("/add")
        self.assertIn(b"That submit was blocked", follow.data)

    def test_add_post_csrf_works_without_origin(self):
        self._login()
        page = self.client.get("/add")
        start = page.data.find(b'name="csrf" value="') + len(b'name="csrf" value="')
        token = page.data[start : page.data.find(b'"', start)].decode()
        self.assertTrue(token)
        started = {"ran": False}

        def fake_provision(*_a, **_k):
            started["ran"] = True
            return {
                "ok": True,
                "domain": "ok.example",
                "email": "hi@ok.example",
                "local_part": "hi",
                "password": "",
                "records": [],
            }

        self.webapp.provision = fake_provision
        opened = self.client.post(
            "/add",
            data={"domain": "ok.example", "local_part": "hi", "provider": "manual", "csrf": token},
        )
        self.assertEqual(opened.status_code, 302)
        self.assertIn("/job/", opened.headers["Location"])


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
