"""Labeled sample Red Herring Prospectus + ticket log.

The attached prospectus was not in the repository, so this fixture is the
single source of truth for the sample document and for gold-standard labels.
Ticket / order / CIN / application numbers are operational IDs, not PII.
"""

PREFERRED_FAKES = {
    "Rashi Patil": "John Doe",
    "rashhi.patil@gmail.com": "john.doe@example.com",
    "Rohan Dey": "Peter Parker",
    "rohan.dey@gmail.com": "peter.parker@example.com",
    "+91 9876543210": "+91 1234567645",
}

COMPANY = {
    "legal_name": "Nova Tech Analytics Private Limited",
    "cin": "U72900MH2018PTC123456",
    "registered_office": (
        "42, 5th Floor, Sunrise Towers, Linking Road, "
        "Bandra West, Mumbai 400050, Maharashtra, India"
    ),
    "corporate_office": "18 MG Road, Koramangala, Bengaluru 560034, Karnataka, India",
    "phone": "+91 9876543210",
    "email": "rashhi.patil@gmail.com",
    "website": "www.novatechanalytics.example",
    "incorporation_date": "15 August 2018",
    "prospectus_date": "August 13, 2026",
    "offer_size": "Rs. 2,500 million",
    "face_value": "Rs. 5",
}

PEOPLE = [
    {
        "name": "Rashi Patil",
        "role": "Whole-time Director, Company Secretary and Compliance Officer",
        "dob": "14 March 1992",
        "email": "rashhi.patil@gmail.com",
        "phone": "+91 9876543210",
        "address": "12 Palm Grove, Juhu, Mumbai 400049, India",
        "ssn": "123-45-6789",
        "cc": "4111 1111 1111 1111",
        "ip": "203.0.113.45",
    },
    {
        "name": "Rohan Dey",
        "role": "Non-Executive Director",
        "dob": "02/07/1988",
        "email": "rohan.dey@gmail.com",
        "phone": "+91 9123456780",
        "address": (
            "Flat 7B, Lake View Apartments, Salt Lake Sector V, "
            "Kolkata 700091, India"
        ),
        "ssn": "456-12-7890",
        "cc": "5500-0000-0000-0004",
        "ip": "198.51.100.23",
        "company": "Dey Consulting LLP",
    },
    {
        "name": "Meera Sharma",
        "role": "Independent Director",
        "dob": "1980-11-21",
        "email": "meera.sharma@novatech.example",
        "phone": "+91 9988776655",
        "address": "221 Baker Street, Bengaluru 560001, India",
        "ip": "192.0.2.10",
    },
    {
        "name": "Arjun Kapoor",
        "role": "Chief Financial Officer",
        "dob": "05 January 1985",
        "email": "arjun.kapoor@kapoordigital.example",
        "phone": "(415) 555-2671",
        "address": "9 Residency Road, Shivajinagar, Pune 411005, India",
        "company": "Kapoor Digital Inc.",
        "ip": "198.51.100.77",
    },
]

TICKETS = [
    {"id": "TKT-441902", "order_id": "ORD-77821", "person": PEOPLE[0]},
    {"id": "TKT-441903", "order_id": "ORD-77822", "person": PEOPLE[1]},
    {"id": "TKT-441904", "order_id": "ORD-77823", "person": PEOPLE[2]},
    {"id": "TKT-441905", "order_id": "ORD-77824", "person": PEOPLE[3]},
]

NON_PII = [
    COMPANY["cin"],
    COMPANY["incorporation_date"],
    COMPANY["prospectus_date"],
    COMPANY["offer_size"],
    COMPANY["face_value"],
    COMPANY["website"],
    "TKT-441902",
    "TKT-441903",
    "TKT-441904",
    "TKT-441905",
    "ORD-77821",
    "ORD-77822",
    "ORD-77823",
    "ORD-77824",
    "APP-908812",
    "Section 32",
    "Companies Act, 2013",
    "RED HERRING PROSPECTUS",
    "Book Built Issue",
    "SEBI",
]


def gold_entities():
    """Unique (type, value) gold labels derived from the fixture."""
    items = []

    def add(pii_type, value):
        if value and (pii_type, value) not in {(i["type"], i["value"]) for i in items}:
            items.append({"type": pii_type, "value": value})

    add("company", COMPANY["legal_name"])
    add("address", COMPANY["registered_office"])
    add("address", COMPANY["corporate_office"])
    add("phone", COMPANY["phone"])
    add("email", COMPANY["email"])

    for person in PEOPLE:
        add("name", person["name"])
        add("email", person["email"])
        add("phone", person["phone"])
        add("address", person["address"])
        add("date_of_birth", person["dob"])
        if person.get("ssn"):
            add("ssn", person["ssn"])
        if person.get("cc"):
            add("credit_card", person["cc"])
        if person.get("ip"):
            add("ip_address", person["ip"])
        if person.get("company"):
            add("company", person["company"])

    return items
