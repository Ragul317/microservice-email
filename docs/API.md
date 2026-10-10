# API Reference

All bodies are JSON (`Content-Type: application/json`).

Error responses from both services share one shape:

```json
{
  "success": false,
  "message": "Human-readable summary",
  "errors": [{ "field": "to", "message": "value is not a valid email address: ..." }]
}
```

`errors` is only present for validation errors (HTTP 422).

## Validation rules (both services)

| Field | Rule |
|---|---|
| `to` | Required, valid email address |
| `subject` | Required, 1–200 characters after trimming, must not contain line breaks |
| `message` (backend) / `body` (email service) | Required, 1–10,000 characters after trimming |

---

## Main Backend — `http://localhost:8000`

### `POST /send`
Sends an email by delegating to the Email Microservice.

Request:
```json
{
  "to": "customer@example.com",
  "subject": "Test Email",
  "message": "Hello from the application"
}
```

Success: **200**
```json
{
  "success": true,
  "message": "Email sent successfully"
}
```

| Status | When | `message` |
|---|---|---|
| 200 | Email accepted by the SMTP provider | `Email sent successfully` |
| 422 | Missing or invalid field | `Validation failed` (+ `errors`) |
| 502 | Email Microservice responded with an error (SMTP auth or send failure, rejected request) | Forwarded clean message from the Email Microservice, e.g. `Email sending failed` |
| 503 | Email Microservice unreachable (connection refused or DNS failure) | `Email service is unavailable. Please try again later.` |
| 504 | Email Microservice did not respond within `EMAIL_SERVICE_TIMEOUT` | `Email service timed out. Please try again later.` |
| 500 | Unexpected error in the backend | `Internal server error` |

### `GET /health`
**200**
```json
{ "status": "healthy" }
```
This only checks the backend itself. It does not call the Email Microservice.

### `GET /`
Serves the frontend (`frontend/index.html`, plus `/style.css` and `/app.js`).

---

## Email Microservice — `http://localhost:8001`

Internal service. Only the Main Backend should call it.

### `POST /send-email`

Request:
```json
{
  "to": "customer@example.com",
  "subject": "Test Email",
  "body": "Hello from the Email Microservice"
}
```

Success: **200**
```json
{
  "success": true,
  "message": "Email sent successfully"
}
```

| Status | When | `message` |
|---|---|---|
| 200 | SMTP server accepted the message | `Email sent successfully` |
| 400 | SMTP server refused the recipient | `Recipient address was rejected` |
| 422 | Missing or invalid field | `Validation failed` (+ `errors`) |
| 500 | SMTP settings missing in the environment | `Email service is not configured` |
| 502 | SMTP authentication failed | `Email provider authentication failed` |
| 502 | SMTP error while sending | `Email sending failed` |
| 503 | Could not connect to the SMTP server (refused, DNS, timeout) | `Could not connect to email provider` |
| 500 | Unexpected error | `Internal server error` |

Internal SMTP error details are written to the service log only. They are never returned.

### `GET /health`
**200**
```json
{ "status": "healthy" }
```
This does not connect to SMTP.

---

## Failure scenarios end to end

| Scenario | Email service | Backend → frontend | Frontend shows |
|---|---|---|---|
| Invalid email typed | — | (blocked client-side) | Field error |
| Invalid payload sent directly to backend | — | 422 | Field errors |
| Email service not running | — | 503 | "Email service is unavailable…" |
| Email service hangs | — | 504 | "Email service timed out…" |
| Wrong SMTP password | 502 | 502 | "Email provider authentication failed" |
| SMTP host unreachable | 503 | 502 | "Could not connect to email provider" |
| Backend not running | — | (network error) | "Backend unavailable…" |
