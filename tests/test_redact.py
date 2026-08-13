from redact import Redactor, luhn_ok


def redact(text: str, **kwargs) -> str:
    return Redactor(**kwargs).redact_text(text)[0]


def findings(text: str):
    return Redactor().find(text)


def test_email_and_seeded_name():
    text = "Rashi Patil wrote to rashhi.patil@gmail.com"
    out = redact(text)
    assert "Rashi Patil" not in out
    assert "rashhi.patil@gmail.com" not in out
    assert "John Doe" in out
    assert "john.doe@example.com" in out


def test_phone_seeded():
    out = redact("Call +91 9876543210 now")
    assert "+91 9876543210" not in out
    assert "+91 1234567645" in out


def test_rohan_mapping():
    out = redact("Rohan Dey <rohan.dey@gmail.com>")
    assert "Rohan Dey" not in out
    assert "Peter Parker" in out
    assert "peter.parker@example.com" in out


def test_ssn():
    out = redact("SSN 123-45-6789")
    assert "123-45-6789" not in out


def test_credit_card_luhn():
    assert luhn_ok("4111111111111111")
    assert not luhn_ok("4111111111111112")
    out = redact("card 4111 1111 1111 1111")
    assert "4111 1111 1111 1111" not in out


def test_ip_not_version():
    text = "Source IP: 203.0.113.45 and version 1.2.3.4 of the tool"
    found = findings(text)
    ips = [f.original for f in found if f.pii_type == "ip_address"]
    assert "203.0.113.45" in ips
    assert "1.2.3.4" not in ips


def test_dob_anchored_not_filing_date():
    text = "Date of Birth: 14 March 1992. Prospectus dated August 13, 2026. Incorporated on 15 August 2018."
    out = redact(text)
    assert "14 March 1992" not in out
    assert "August 13, 2026" in out
    assert "15 August 2018" in out


def test_company_and_address():
    text = (
        "Nova Tech Analytics Private Limited. "
        "Registered Office: 42, 5th Floor, Sunrise Towers, Linking Road, "
        "Bandra West, Mumbai 400050, Maharashtra, India"
    )
    out = redact(text)
    assert "Nova Tech Analytics Private Limited" not in out
    assert "Sunrise Towers" not in out


def test_short_street_address():
    text = "12 Palm Grove, Juhu, Mumbai 400049, India"
    out = redact(text)
    assert "Palm Grove" not in out
    assert "400049" not in out


def test_docx_table_and_footer_are_redacted(tmp_path):
    from build_sample import build
    from redact import redact_docx, extract_docx_text
    from sample_data import PREFERRED_FAKES, gold_entities
    from docx import Document

    source = build()
    output = tmp_path / "out.docx"
    redact_docx(source, output, Redactor(preferred=PREFERRED_FAKES, seed=42))
    xml = Document(output).element.xml
    for entity in gold_entities():
        assert entity["value"] not in xml, entity
    text = extract_docx_text(output)
    assert "TKT-441902" in text
    assert "Nova Tech Analytics Private Limited" not in text


def test_ticket_and_order_not_redacted():
    text = "Ticket ID: TKT-441902 Order ID: ORD-77821 CIN U72900MH2018PTC123456 APP-908812"
    out = redact(text)
    assert "TKT-441902" in out
    assert "ORD-77821" in out
    assert "U72900MH2018PTC123456" in out
    assert "APP-908812" in out


def test_stable_replacements():
    redactor = Redactor(seed=7)
    first, _ = redactor.redact_text("Email meera.sharma@novatech.example please")
    second, _ = redactor.redact_text("Also meera.sharma@novatech.example again")
    assert "meera.sharma@novatech.example" not in first
    a = first.replace("Email ", "").replace(" please", "")
    b = second.replace("Also ", "").replace(" again", "")
    assert a == b


def test_us_phone():
    out = redact("Call (415) 555-2671")
    assert "(415) 555-2671" not in out


def test_company_keeps_inc_period():
    out = redact("He founded Kapoor Digital Inc. last year")
    assert "Kapoor Digital Inc." not in out


def test_company_does_not_eat_previous_heading():
    text = "Book Built Issue\nNova Tech Analytics Private Limited"
    companies = [f.original for f in findings(text) if f.pii_type == "company"]
    assert companies == ["Nova Tech Analytics Private Limited"]
