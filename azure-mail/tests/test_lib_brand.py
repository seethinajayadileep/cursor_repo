import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
