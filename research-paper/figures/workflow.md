# Fig. 2. Website scanning workflow of WebSentinel.

Solid steps are implemented in the current prototype. Dashed steps are proposed for the remaining capstone work.

```mermaid
flowchart TD
    A["1. User submits or opens a URL"] --> B["2. Validate and normalize URL"]
    B --> C{"HTTP or HTTPS?"}
    C -->|No| Z["Reject: unsupported scheme"]
    C -->|Yes| D["3. Safe-scan policy checks"]
    D --> E["4. Collect HTTP / protocol signal"]
    E --> F["5. Inspect TLS certificate"]
    F --> G["6. Retrieve domain registration / age"]
    G --> H["7. Proposed: DNS, IP, redirects, technologies"]
    H --> I["8. Proposed: approved reputation sources"]
    I --> J["9. Extract phishing features"]
    J --> K["10. Rule-based indicators"]
    K --> L["11. Proposed: ML prediction if enabled"]
    L --> M["12. Combine into risk score"]
    M --> N["13. Generate explanations"]
    N --> O["14. Proposed: store scan in PostgreSQL"]
    O --> P["15. Present dashboard / popup"]
    P --> Q["16. Proposed: generate downloadable report"]

    style H stroke-dasharray: 5 5
    style I stroke-dasharray: 5 5
    style L stroke-dasharray: 5 5
    style O stroke-dasharray: 5 5
    style Q stroke-dasharray: 5 5
```

**Caption (IEEE):** Fig. 2. End-to-end website scanning workflow. Dashed stages are planned and are not claimed as implemented.

**Prototype mapping:**
1. Chrome `activeTab` reads the current tab URL.
2. Client and server reject `chrome:`, `file:`, and non-`http(s)` schemes.
3. Path and query are stripped; only `scheme + hostname` is sent.
4--6. Protocol, `ssl-checker`, and WHOIS scrape run with 8 s timeouts.
7--16 except scoring/UI: not implemented in the inspected repository.
