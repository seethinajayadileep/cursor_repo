import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vm"))
from lib_brand import DnsRecord, apex_host, format_records, mail_records  # noqa: E402


class RecordTests(unittest.TestCase):
    def test_apex_host_strips_suffix(self):
        self.assertEqual(apex_host("example.com", "example.com"), "")
        self.assertEqual(apex_host("selector1._domainkey.example.com", "example.com"), "selector1._domainkey")
        self.assertEqual(apex_host("@", "example.com"), "")
        self.assertEqual(apex_host("", "example.com"), "")

    def test_mail_records_prepend_mx(self):
        acs = [DnsRecord(type="TXT", host="", value="v=spf1 include:spf.protection.outlook.com -all", kind="SPF")]
        recs = mail_records("brand.com", "mail.seethinajayadileep.dev", acs)
        self.assertEqual(recs[0].type, "MX")
        self.assertEqual(recs[0].value, "mail.seethinajayadileep.dev.")
        self.assertEqual(recs[0].priority, 10)
        self.assertEqual(format_records(recs)[0]["host"], "@")
        self.assertEqual(recs[-1].kind, "DMARC")
        self.assertEqual(recs[-1].host, "_dmarc")

    def test_dns_rows_skip_empty(self):
        from lib_brand import dns_rows, records_ready

        empty = {"properties": {"verificationRecords": {"Domain": {"value": ""}, "SPF": {}}}}
        self.assertFalse(records_ready(empty))
        self.assertEqual(dns_rows(empty, "brand.com"), [])
        ready = {
            "properties": {
                "provisioningState": "Succeeded",
                "verificationRecords": {
                    "Domain": {"type": "TXT", "name": "brand.com", "value": "ms-domain-verification=abc"},
                    "SPF": {"type": "TXT", "name": "@", "value": "v=spf1 include:spf.protection.outlook.com -all"},
                    "DKIM": {
                        "type": "CNAME",
                        "name": "selector1-azurecomm-net._domainkey.brand.com",
                        "value": "selector1-azurecomm-net._domainkey.contoso.azurecomm.net",
                    },
                    "DKIM2": {
                        "type": "CNAME",
                        "name": "selector2-azurecomm-net._domainkey.brand.com",
                        "value": "selector2-azurecomm-net._domainkey.contoso.azurecomm.net",
                    },
                },
            }
        }
        self.assertTrue(records_ready(ready))
        rows = dns_rows(ready, "brand.com")
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[2].host, "selector1-azurecomm-net._domainkey")

    def test_save_domain_roundtrip(self):
        import tempfile
        from pathlib import Path
        from lib_brand import load_domains, save_domain

        p = Path(tempfile.mkdtemp()) / "domains.json"
        save_domain({"domain": "Brand.com", "email": "a@brand.com"}, p)
        store = load_domains(p)
        self.assertEqual(store["brand.com"]["email"], "a@brand.com")

    def test_lookup_without_azure_is_mx_only(self):
        from lib_brand import lookup_dns

        rows = lookup_dns({"MAIL_HOSTNAME": "mail.example.com"}, "brand.com")
        self.assertEqual(rows[0]["type"], "MX")
        self.assertEqual(rows[0]["value"], "mail.example.com.")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[-1]["host"], "_dmarc")


class VerifyLinkTests(unittest.TestCase):
    def test_can_link_sender_only_needs_domain(self):
        from lib_brand import can_link_domain, can_link_sender, check_failed, link_refused

        self.assertTrue(can_link_sender({"Domain": "Verified", "SPF": "NotStarted"}))
        self.assertFalse(can_link_sender({"Domain": "VerificationFailed", "SPF": "Verified"}))
        self.assertFalse(can_link_sender({"Domain": "VerificationInProgress"}))
        self.assertFalse(can_link_sender({}))
        self.assertFalse(
            can_link_domain({"Domain": "Verified", "SPF": "VerificationInProgress", "DKIM": "Verified", "DKIM2": "Verified"})
        )
        self.assertTrue(
            can_link_domain({"Domain": "Verified", "SPF": "Verified", "DKIM": "Verified", "DKIM2": "Verified"})
        )
        self.assertTrue(check_failed("VerificationFailed"))
        self.assertFalse(check_failed("Verified"))
        self.assertTrue(link_refused(RuntimeError("PATCH ... PatchDomainLinkingError ... could not be linked")))
        self.assertFalse(link_refused(RuntimeError("401 unauthorized")))

    @patch("lib_brand.time.sleep")
    @patch("lib_brand.link_and_mailfrom")
    @patch("lib_brand._initiate")
    @patch("lib_brand.verification_status")
    def test_verify_acs_retries_failed_domain_and_links_early(self, status, initiate, link, _sleep):
        from lib_brand import verify_acs

        status.side_effect = [
            {
                "Domain": "VerificationFailed",
                "SPF": "NotStarted",
                "DKIM": "NotStarted",
                "DKIM2": "NotStarted",
            },
            {
                "Domain": "Verified",
                "SPF": "VerificationInProgress",
                "DKIM": "NotStarted",
                "DKIM2": "NotStarted",
            },
            {
                "Domain": "Verified",
                "SPF": "Verified",
                "DKIM": "Verified",
                "DKIM2": "Verified",
            },
        ]
        logs: list[str] = []
        out = verify_acs({"AZURE_SUBSCRIPTION_ID": "sub"}, "phronen.com", ["ruthwik"], logs.append)
        self.assertEqual(out["Domain"], "Verified")
        link.assert_called()
        self.assertEqual(link.call_count, 1)
        self.assertEqual(link.call_args.args[1], "phronen.com")
        self.assertEqual(link.call_args.args[2], ["ruthwik"])
        kinds = [c.args[2] for c in initiate.call_args_list]
        self.assertIn("Domain", kinds)
        self.assertTrue(any("will not link mailboxCs" in line for line in logs))

    @patch("lib_brand.az")
    def test_link_and_mailfrom_appends_and_keeps_other_domains(self, az):
        from lib_brand import link_and_mailfrom

        existing = (
            "/subscriptions/sub/resourceGroups/mailboxRg/providers/"
            "Microsoft.Communication/emailServices/mail-box/domains/other.com"
        )
        az.side_effect = [
            {"properties": {"linkedDomains": [existing]}},
            {},
            {},
        ]
        logs: list[str] = []
        env = {"AZURE_SUBSCRIPTION_ID": "sub", "RESOURCE_GROUP": "mailboxRg"}
        link_and_mailfrom(env, "phronen.com", ["ruthwik"], logs.append)
        patch = az.call_args_list[1]
        self.assertEqual(patch.args[1], "PATCH")
        linked = patch.args[4]["properties"]["linkedDomains"]
        self.assertIn(existing, linked)
        self.assertTrue(any("phronen.com" in item for item in linked))
        mailfrom = az.call_args_list[2]
        self.assertEqual(mailfrom.args[1], "PUT")
        self.assertIn("senderUsernames/ruthwik", mailfrom.args[2])

    @patch("lib_brand.az")
    def test_link_and_mailfrom_explains_patch_domain_linking_error(self, az):
        from lib_brand import link_and_mailfrom

        az.side_effect = [
            {"properties": {"linkedDomains": []}},
            RuntimeError(
                "PATCH https://management.azure.com/... -> 400 "
                "b'{\"error\":{\"code\":\"PatchDomainLinkingError\",\"message\":\"Requested domain could not be linked\"}}'"
            ),
        ]
        logs: list[str] = []
        env = {"AZURE_SUBSCRIPTION_ID": "sub", "RESOURCE_GROUP": "mailboxRg"}
        link_and_mailfrom(env, "talentql.org", ["hi"], logs.append)
        self.assertTrue(any("PatchDomainLinkingError" in line for line in logs))
        self.assertTrue(any("SPF" in line and "DKIM" in line for line in logs))

    @patch("lib_brand.mailcow")
    def test_mail_directory_groups_mailboxes_by_domain(self, mailcow_api):
        from lib_brand import mail_directory, save_domain

        mailcow_api.side_effect = [
            [
                {"domain_name": "phronen.com", "active": "1"},
                {"domain_name": "arambh.ventures", "active": "1"},
            ],
            [
                {
                    "username": "ruthwik@phronen.com",
                    "local_part": "ruthwik",
                    "domain": "phronen.com",
                    "name": "ruthwik",
                    "active": "1",
                },
                {
                    "username": "akruti@arambh.ventures",
                    "local_part": "akruti",
                    "domain": "arambh.ventures",
                    "name": "akruti",
                    "active": "1",
                },
            ],
        ]
        p = Path(tempfile.mkdtemp()) / "domains.json"
        import lib_brand

        prev = lib_brand.DOMAINS_PATH
        lib_brand.DOMAINS_PATH = p
        try:
            save_domain({"domain": "phronen.com", "email": "ruthwik@phronen.com", "verified": True}, p)
            data = mail_directory(
                {
                    "MAIL_HOSTNAME": "mail.example",
                    "MAILCOW_API_URL": "https://mail.example",
                    "MAILCOW_API_KEY": "k",
                }
            )
            names = [d["domain"] for d in data["domains"]]
            self.assertEqual(names, ["arambh.ventures", "phronen.com"])
            phronen = next(d for d in data["domains"] if d["domain"] == "phronen.com")
            self.assertEqual(phronen["mailboxes"][0]["email"], "ruthwik@phronen.com")
            self.assertTrue(phronen["send_ready"])
            self.assertEqual(data["mailbox_count"], 2)
            self.assertIsNone(data["error"])
        finally:
            lib_brand.DOMAINS_PATH = prev

    def test_webmail_ticket_is_signed_and_mailbox_known(self):
        from lib_brand import mailbox_known, webmail_sso_url, webmail_ticket

        secret = "a" * 32
        ticket = webmail_ticket("ruthwik@phronen.com", secret, now=1_700_000_000, ttl=90)
        self.assertTrue(ticket.startswith("1700000090."))
        other = webmail_ticket("ashish@ciphrix.org", secret, now=1_700_000_000, ttl=90)
        self.assertNotEqual(ticket, other)
        env = {
            "MAIL_HOSTNAME": "mail.example",
            "WEB_SSO_SECRET": secret,
            "MAILCOW_API_URL": "",
            "MAILCOW_API_KEY": "",
        }
        url = webmail_sso_url(env, "ruthwik@phronen.com", now=1_700_000_000)
        self.assertIn("https://mail.example/mailbox-sso.php?", url)
        self.assertIn("u=ruthwik%40phronen.com", url)
        self.assertIn("t=1700000090.", url)
        p = Path(tempfile.mkdtemp()) / "domains.json"
        import lib_brand

        prev = lib_brand.DOMAINS_PATH
        lib_brand.DOMAINS_PATH = p
        try:
            lib_brand.save_domain({"domain": "phronen.com", "email": "ruthwik@phronen.com"}, p)
            self.assertTrue(mailbox_known({"MAILCOW_API_URL": ""}, "ruthwik@phronen.com"))
            self.assertFalse(mailbox_known({"MAILCOW_API_URL": ""}, "nobody@phronen.com"))
        finally:
            lib_brand.DOMAINS_PATH = prev


if __name__ == "__main__":
    unittest.main()
