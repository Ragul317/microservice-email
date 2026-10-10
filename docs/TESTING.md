# Testing

## Automated tests

These use `pytest` with FastAPI's `TestClient`. **No real email is sent and no network is used:**
- The Email Microservice tests replace `smtplib.SMTP` with a fake class, so the real sender code (message building, STARTTLS, login, error mapping) still runs.
- The Main Backend tests swap the shared `httpx.AsyncClient` for one backed by `httpx.MockTransport`, through FastAPI dependency override.

Run each suite from its own directory with its own virtualenv:

```bash
cd email-service && .venv/bin/python -m pytest -v
cd backend       && .venv/bin/python -m pytest -v
```

### Email Microservice (`email-service/tests/`)

| Test | Expectation |
|---|---|
| Health endpoint | 200 `{"status":"healthy"}`, no SMTP connection |
| Valid `/send-email` | 200 success; STARTTLS, login and send_message called; headers correct |
| SSL mode (`SMTP_USE_SSL=true`) | Uses `SMTP_SSL`, no STARTTLS |
| Invalid email | 422 with an `errors[].field == "to"` |
| Missing `to` / `subject` / `body` | 422 |
| Blank subject or body, line break in subject | 422 |
| SMTP connection failure | 503, generic message |
| SMTP authentication failure | 502 `Email provider authentication failed` |
| SMTP sending failure | 502 `Email sending failed` |
| Recipient refused | 400 |
| SMTP not configured | 500 `Email service is not configured` |
| Unexpected exception | 500, no internal details leaked |

### Main Backend (`backend/tests/`)

| Test | Expectation |
|---|---|
| Health endpoint | 200 `{"status":"healthy"}` |
| Frontend served at `/` | 200 HTML containing the form |
| Valid `/send` | 200 success; upstream receives `{to, subject, body}` at `/send-email` |
| Missing email | 422 |
| Invalid email | 422 |
| Missing / blank subject | 422 |
| Missing / blank message | 422 |
| Email service unavailable (`ConnectError`) | 503 |
| Email service timeout (`TimeoutException`) | 504 |
| Email service returns an error (502) | 502 with the upstream's clean message |
| Email service returns 200 with a non-JSON body | 502 |

## Manual integration checks

With both services running (see [SETUP.md](SETUP.md)):

```bash
curl -s localhost:8000/health
curl -s localhost:8001/health
curl -s localhost:8000/ | head -5                       # HTML form
curl -s -X POST localhost:8000/send -H 'Content-Type: application/json' \
     -d '{"to":"not-an-email","subject":"x","message":"y"}'   # 422
# stop the email service, then:
curl -s -X POST localhost:8000/send -H 'Content-Type: application/json' \
     -d '{"to":"a@example.com","subject":"x","message":"y"}'  # 503
```

## Manual end-to-end test (real email)

1. Configure `email-service/.env` with real SMTP credentials (see SETUP.md).
2. Start the Email Microservice (:8001) and the Main Backend (:8000).
3. Open http://localhost:8000.
4. Enter a real recipient, the subject `Test Email`, and the message `Hello from my microservice application`. Click **Send Email**.
5. Expect **✓ Email sent successfully** in the page, and these log lines in order:
   - backend: `Send request received` → `Calling email service` → `Email sent via email service`
   - email-service: `Send-email request received` → `Email sent`
6. Confirm the email arrives in the recipient's inbox (check spam).

## Results

| Run (2026-10-08) | Result |
|---|---|
| `email-service` pytest | 19 passed |
| `backend` pytest | 17 passed (also re-run with a real `.env` present: the tests still use fake config and send nothing) |
| Live: health, `/`, 422, CORS | Pass |
| Live: email service stopped → 503 | Pass |
| Live: email service hanging, `EMAIL_SERVICE_TIMEOUT=2` → 504 after 2.0s | Pass |
| Live E2E via `POST /send` with Gmail SMTP | 200 `Email sent successfully` (about 4.3s), logged on both services |
| Browser form click-through | Done manually by the user (no browser automation in the build session) |
