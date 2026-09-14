# Fig. 1. WebSentinel system architecture (solid = implemented, dashed = planned).

The diagram below is source for later conversion into an IEEE two-column figure. Solid boxes denote modules in the *proposed* capstone architecture. The current prototype implements only the subset marked `(P)`.

```mermaid
flowchart TB
    User["User / Analyst"] --> UI["React dashboard<br/>or Chrome extension (P)"]
    UI --> API["REST API<br/>Proposed: FastAPI<br/>Prototype: Express.js (P)"]
    API --> SM["Scan Manager"]
    API --> Q["Background queue<br/>Redis + Celery/RQ"]

    SM --> WA["Website Analyzer (P: origin only)"]
    SM --> COL["Security Data Collectors"]

    COL --> HTTP["HTTP / protocol (P)"]
    COL --> DNS["DNS records"]
    COL --> RDAP["RDAP / domain registration (P: WHOIS scrape)"]
    COL --> SSL["SSL/TLS (P)"]
    COL --> RED["Redirect analyzer"]
    COL --> TECH["Technology detection"]
    COL --> IP["IP / hosting / geo"]
    COL --> TI["Reputation / threat intelligence"]

    WA --> FE["Feature Extraction"]
    HTTP --> FE
    DNS --> FE
    RDAP --> FE
    SSL --> FE
    RED --> FE
    TECH --> FE
    IP --> FE
    TI --> FE

    FE --> RULE["Rule-based engine (P)"]
    FE --> ML["ML phishing model"]
    RULE --> RISK["Risk scoring engine (P)"]
    ML --> RISK
    RISK --> XAI["Explainability module (P: rule reasons)"]
    XAI --> DB["PostgreSQL"]
    XAI --> RPT["Security report"]
    DB --> UI
    RPT --> UI
    Q -.-> COL
```

**Caption (IEEE):** Fig. 1. Proposed architecture of the WebSentinel security assessment system. Modules marked (P) are present in the current Chrome-extension prototype.

**Status note:** FastAPI, React, PostgreSQL, Redis, Celery/RQ, DNS, RDAP client, redirect, technology, IP/hosting, threat-intelligence, ML, SHAP, and report-generation modules are *proposed*. The prototype uses Express.js, a Manifest V3 popup, HTTPS/SSL/WHOIS collectors, and a rule-based score.
