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
        self.assertIn(b"I will paste DNS myself", add.data)
        prov = self.client.get("/providers")
        self.assertIn(b"Cloudflare", prov.data)
        self.assertIn(b"Namecheap", prov.data)


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
