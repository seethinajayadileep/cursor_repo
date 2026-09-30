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

    def test_lookup_without_azure_is_mx_only(self):
        from lib_brand import lookup_dns

        rows = lookup_dns({"MAIL_HOSTNAME": "mail.example.com"}, "brand.com")
        self.assertEqual(rows[0]["type"], "MX")
        self.assertEqual(rows[0]["value"], "mail.example.com.")
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
