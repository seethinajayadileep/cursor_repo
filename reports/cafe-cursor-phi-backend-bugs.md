# Cafe Cursor Buenos Aires #4 — backend bug report

Live app: https://cafe-cursor-phi.vercel.app/?referrer=luma&utm_source=luma

This is a Next.js (App Router) credit-claim site on Vercel. Attendees enter the name + email they used on Luma; the server checks an eligible-guest list and emails a Cursor credit. Source is not in this repository and was not found on GitHub, so this is a black-box review of the public API and client bundles.

Reviewed: `GET`/`POST /api/register`, `GET`/`POST`/`DELETE /api/admin/auth`, `GET /api/admin/dashboard`, `POST /api/admin/actions`, `/admin`, `/admin/dashboard`, and the public JS for those pages.

No credits were claimed, no guest list was enumerated, and no admin credentials were guessed.

---

## Backend surface

| Method | Path | Auth | Role |
|---|---|---|---|
| `GET` | `/api/register` | none | Availability badge (`remaining`, `stats`) |
| `POST` | `/api/register` | none (email is the identity) | Claim / re-request a credit |
| `GET` | `/api/admin/auth` | cookie | `{ authenticated: boolean }` |
| `POST` | `/api/admin/auth` | username + password | Login |
| `DELETE` | `/api/admin/auth` | none required | Always returns logout success |
| `GET` | `/api/admin/dashboard` | cookie | Eligible users + credit pool (401 without session) |
| `POST` | `/api/admin/actions` | cookie | `ADD_ELIGIBLE_USER`, `ADD_CREDIT`, `ASSIGN_CREDIT`, `REVOKE_CREDIT`, `SEND_CREDIT_EMAIL` |

`POST /api/register` body (from the client): `{ name, email, locale }`.

Success UI only renders a credit URL when `isTest && credit`. Real claims are supposed to be email-only (`emailPrivacyNote`).

---

## High

### 1. Name regex rejects real attendee names (claim is impossible)

`POST /api/register` validates name **before** eligibility.

Observed:

| Name | Result |
|---|---|
| `José María` | accepted by name rule (fails later on email format) |
| `A` | `El nombre debe tener al menos 2 caracteres` |
| `Ada2` | `El nombre solo puede contener letras` |
| `Maria-Jose` | `El nombre solo puede contener letras` |
| `O'Brien` | `El nombre solo puede contener letras` |
| `Dr. Ada` | `El nombre solo puede contener letras` |
| 5000× `"Ana "` | `El nombre no puede exceder 100 caracteres` |

People whose legal / Luma name has a hyphen, apostrophe, or period cannot claim, and cannot retry email delivery either.

**Fix:** Allow letters, combining marks, spaces, hyphen, apostrophe, and `.`. Keep the length cap. Do not run the name charset check on an already-claimed re-request if the email is the account key.

### 2. Distinct `POST /api/register` errors are an email-membership oracle

The client maps these codes:

- `NOT_ELIGIBLE` — email not on the event list (`HTTP 403`)
- `NOT_APPROVED` — Luma registration not approved
- `NO_CREDITS` — pool empty
- `EMAIL_DELIVERY_FAILED` — credit reserved, mail failed
- `VALIDATION_ERROR` / `SERVER_ERROR`

Anyone can submit a name + email and learn whether that address is on the approved list. Combined with public Luma guest names, this is a membership check.

**Fix:** Return one generic failure for “cannot issue a credit” (`NOT_ELIGIBLE` / `NOT_APPROVED` / unknown). Keep `EMAIL_DELIVERY_FAILED` only after a successful authenticated claim. Rate-limit by IP **and** email.

---

## Medium

### 3. Invalid JSON is a 500, not a 400

`POST /api/register` with body `notjson` and `Content-Type: application/json`:

```http
HTTP/2 500
{"success":false,"error":"Error interno del servidor. Por favor intenta de nuevo.","code":"SERVER_ERROR"}
```

Same pattern on `POST /api/admin/auth` (`"Error interno del servidor"`).

This is an uncaught `JSON.parse` / Zod parse. It is also a cheap way to generate 500s.

**Fix:** Wrap body parsing; return `400` + `VALIDATION_ERROR` for malformed JSON.

### 4. `locale` is ignored; Zod internals leak in English

`POST` with `"locale":"en"` still returns Spanish copy (`Ingresa un correo electrónico válido`, etc.).

Schema failures are raw Zod English:

- `"Required"`
- `"Expected object, received array"`
- `"Expected string, received null"`

The claim UI only translates `NOT_ELIGIBLE`, `NOT_APPROVED`, `NO_CREDITS`, `EMAIL_DELIVERY_FAILED`, `NETWORK_ERROR`. Everything else (including `VALIDATION_ERROR` and `SERVER_ERROR`) is shown as the raw server string, so an English UI still shows Spanish or Zod English.

**Fix:** Honor `locale` (`es` / `en`). Map Zod issues to stable codes. Add `VALIDATION_ERROR` and `SERVER_ERROR` to the client switch.

### 5. Credit URL may still be in the JSON even when the UI hides it

The success view does:

```js
let r = !!(m.isTest && m.credit);
// credit link / copy / “Use credit” only render when r is true
```

Production copy says the link is email-only. If `POST /api/register` still includes `credit` on `success` / `isExisting` for non-test users, anyone who knows an attendee email can read the referral URL from the response body (Network tab), same class of bug as cafe-cursor-salta.

This was **not** confirmed against a real attendee email (no claims, no re-fetch of live codes).

**Fix:** Never put `credit` / referral URLs in the public JSON except for `isTest: true`. Re-requests should only return `emailSent` / `isExisting`.

### 6. `EMAIL_DELIVERY_FAILED` reserves a credit without proving delivery

Client copy: *“Your credit was reserved, but we could not send the email. Try again; another credit will not be assigned.”*

If send fails after assign, the attendee is blocked from another code and may never receive the link unless retry works. Retry does not clear the form (good), but there is no admin-visible guarantee in the public API that the reserved row is recoverable.

**Fix:** Assign the code only after a successful send, or keep it in `reserved_unsent` and always allow `SEND_CREDIT_EMAIL` retry. Log `emailSentAt` (already on the admin user object).

---

## Low

### 7. `DELETE /api/admin/auth` succeeds with no session

Unauthenticated:

```json
{"success":true,"message":"Sesión cerrada correctamente"}
```

Harmless, but it pretends a session was closed. Return `401` or `{ authenticated: false }` when there was no cookie.

### 8. Admin UI is client-gated; APIs are protected (good) but the data model is public

- `GET /api/admin/dashboard` → `401 {"error":"No autorizado"}` without a cookie
- `POST /api/admin/actions` → `401` even on invalid JSON (auth checked first — good)
- `/admin` and `/admin/dashboard` HTML still `200` (prerendered shells: “Verificando sesión…” / client fetch)

The dashboard bundle documents PII fields the API would return when logged in: `eligibleUsers[].{id,email,name,company,approvalStatus,hasClaimed,credit.code,credit.isTest,emailSentAt}` and `credits[].{code,link,isTest,isUsed,assignedAt}`.

Not an unauthenticated dump. Still: do not ship source maps, and keep session cookies `HttpOnly` / `Secure` / `SameSite=Strict`.

### 9. `GET /api/register` inventory is public

```json
{"available":true,"remaining":89,"stats":{"totalEligible":118,"claimed":61,"pending":57}}
```

The homepage badge already shows remaining + claimed / eligible, so this matches product intent. `pending` is unused by the client. Numbers are consistent (`118 - 61 = 57`). Remaining `89` is the unused code pool (`61 + 89 = 150`), not “unclaimed people”.

### 10. `POST` without `Content-Type` is still parsed

A JSON body with no `Content-Type` (or `text/plain`) is still treated as JSON and runs the eligibility check. Prefer requiring `application/json` and 415 otherwise.

### 11. Homepage sends `Access-Control-Allow-Origin: *`

HTML responses include `access-control-allow-origin: *`. `X-Frame-Options: DENY` is set, so this is not clickjacking. It is unnecessary on a first-party page; drop it unless a real cross-origin client exists. The JSON APIs do not send CORS allow-origin (good).

---

## What is working

- Admin data APIs require a session (`401 No autorizado`).
- Real credits are designed to be emailed, not shown in the form (unlike the older Salta build that painted the referral URL for every re-claim).
- Name length is capped at 100.
- Accented letters are accepted.
- `GET /api/admin/auth` returns `{ authenticated: false }` when logged out (no user object).
- Dummy admin login returns a generic `401 Credenciales inválidas` (no username oracle on that one attempt).

---

## Suggested patch order

1. Catch malformed JSON → `400 VALIDATION_ERROR` on `/api/register` and `/api/admin/auth`.
2. Relax name validation; skip it on email-only re-delivery.
3. Collapse eligibility failures to one public error; rate-limit.
4. Strip `credit` from non-test public responses.
5. Honor `locale` and stop returning raw Zod messages.
6. Make credit assignment transactional with email send.

The Vercel project is `cafe-cursor-phi`. This repo cannot apply those patches; they belong in the Next.js app that owns `/api/register` and `/api/admin/*`.
