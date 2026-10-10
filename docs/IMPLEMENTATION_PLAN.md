# Implementation Plan

> Written before implementation (Phase 1). Deviations found during implementation are listed at the bottom.


## Context
The goal is a small, clean demo of a real microservice architecture. A vanilla HTML/JS form calls a **Main FastAPI backend** (:8000). That backend never touches SMTP. It calls a separate **Email Microservice** (:8001) over REST, and the Email Microservice sends the email through **Gmail SMTP** (App Password, chosen by the user).

**Phase 0 findings:**
- `/home/finstein-emp/Documents/projects/microservice` is empty, with no existing files to keep and no git repo.
- Python 3.12.3, pip 24, venv and ensurepip are OK. Node 22, Docker 29 and git 2.43 are present but not needed.
- FastAPI, httpx and pytest are not installed globally. They will be installed into venvs.
- Ports 8000 and 8001 are free.

## Key decisions
- **One venv per service** (`backend/.venv`, `email-service/.venv`). Each service has its own dependencies, which is the microservice spirit. No Docker, DB or queues.
- **Dependencies:**
  - Email service: `fastapi`, `uvicorn[standard]`, `pydantic[email]` (email-validator), `python-dotenv`, `pytest`, `httpx` (needed by TestClient). SMTP uses the stdlib `smtplib` and `email.message.EmailMessage`.
  - Backend: the same, with `httpx` used for real.
- **Config:** a small `app/config.py` per service. It reads env vars via `python-dotenv` and `os.getenv`, and nothing is hardcoded in business logic.
- **Frontend served by the backend:** `StaticFiles(directory=<repo>/frontend, html=True)` is mounted at `/`, after the API routes. Opening `http://localhost:8000` serves the form.
- **Uniform error shape** in both services: `{"success": false, "message": "...", "errors": [{"field","message"}]?}`. A custom `RequestValidationError` handler keeps the 422 status but returns a cleaner body for the frontend.

## Final structure
```
frontend/        index.html, style.css, app.js
backend/         app/{main.py, config.py, routes/{send.py,health.py}, schemas/email.py, services/email_client.py}
                 tests/{conftest.py,test_health.py,test_send.py}, requirements.txt, .env.example
email-service/   app/{main.py, config.py, routes/{email.py,health.py}, schemas/email.py, services/smtp_sender.py}
                 tests/{conftest.py,test_health.py,test_send_email.py}, requirements.txt, .env.example
docs/            IMPLEMENTATION_PLAN.md, ARCHITECTURE.md, API.md, SETUP.md, TESTING.md
README.md, .gitignore (.env, .venv/, __pycache__/, .pytest_cache/)
```
Each package directory gets an `__init__.py`.

## API contract
| Service | Endpoint | Success | Failures |
|---|---|---|---|
| Backend | `POST /send` `{to, subject, message}` | 200 `{success:true, message:"Email sent successfully"}` | 422 validation · 503 email service unreachable · 504 timeout · 502 email service returned error/failed · 500 unexpected |
| Backend | `GET /health` | 200 `{status:"healthy"}` | — |
| Email svc | `POST /send-email` `{to, subject, body}` | 200 `{success:true, message:"Email sent successfully"}` | 422 validation · 500 SMTP not configured · 502 SMTP auth failed / send failed · 503 SMTP connect failed · 400 recipient refused · 500 unexpected |
| Email svc | `GET /health` | 200 `{status:"healthy"}` (no SMTP call) | — |

**Validation (Pydantic):**
- `to` uses `EmailStr`.
- `subject` is 1–200 chars after stripping, with no CR/LF (this blocks header injection).
- `message`/`body` is 1–10000 chars after stripping.

## Phase 2 — Email Microservice
- `config.py` has `SMTP_HOST`, `SMTP_PORT` (default 587), `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_SSL` (false; true means port 465 with `SMTP_SSL`), `SMTP_TIMEOUT` (10s).
- `services/smtp_sender.py`:
  - `send_email(to, subject, body)` builds an `EmailMessage` and uses `smtplib.SMTP` with `starttls()` (or `SMTP_SSL`), then `login` and `send_message`.
  - It raises typed exceptions (`SMTPConfigError`, `SMTPConnectionError`, `SMTPAuthError`, `SMTPSendError`) that wrap `smtplib` errors, `OSError` and `socket.timeout`.
- `routes/email.py` uses a sync `def` endpoint, so FastAPI runs the blocking smtplib work in its threadpool. It maps the exceptions to the status codes in the table and returns **generic** messages. The internal SMTP details only go to the logs, never to the client.
- **Logging:** "send-email request received", "email sent", and "SMTP failure (type)". The recipient is masked (`c***@example.com`), and passwords are never logged.
- **Checkpoint:** run `pytest` in email-service.

## Phase 3 — Main Backend
- `config.py` has `EMAIL_SERVICE_URL` (http://localhost:8001), `EMAIL_SERVICE_TIMEOUT` (20s, which must exceed the SMTP timeout), and `CORS_ORIGINS` (comma-separated, default `http://localhost:8000,http://127.0.0.1:8000`).
- `main.py` uses a lifespan that creates one shared `httpx.AsyncClient(base_url=EMAIL_SERVICE_URL, timeout=...)` on `app.state`. A `get_http_client` dependency exposes it, and tests override it with an `httpx.MockTransport`, so no extra mock library is needed.
- `CORSMiddleware` gets the explicit origins list, the `GET`/`POST` methods and the `Content-Type` header. There is no `*`.
- `services/email_client.py`:
  - It maps `message` to `body` and POSTs to `/send-email`.
  - `httpx.ConnectError` becomes `EmailServiceUnavailable` (503).
  - `httpx.TimeoutException` becomes `EmailServiceTimeout` (504).
  - A non-2xx or `success:false` response becomes `EmailServiceError` (502, with a clean message).
- **Logging:** "send request received", "calling email service", "email sent", and "email service unavailable/timeout/error".
- **Checkpoint:** run `pytest` in backend.

## Phase 4 — Frontend
- `index.html` has a form with `type=email` To, a text Subject, a textarea Message, a "Send Email" button, and a result area with `aria-live`.
- `app.js`:
  - Client-side validation covers an empty or invalid To (regex plus `checkValidity`), an empty subject and an empty message, with per-field errors.
  - It calls a relative `fetch('/send')` on the same origin, so it only ever talks to the main backend.
  - It shows a loading state with the button disabled.
  - Results:
    - success: "✓ Email sent successfully"
    - 422: field errors
    - 502/503/504: "Email sending failed / service unavailable"
    - network `TypeError`: "Backend unavailable"
- `style.css` is a clean centered card with success and error colors. There are no secrets in JS.

## Phase 5–6 — Integration and testing
- **Automated tests (pytest + TestClient)** cover every case in the request:
  - **Backend:** health, valid send, missing/invalid to, missing subject, missing message, service unavailable (ConnectError), timeout (TimeoutException), and an upstream 502.
  - **Email service:** health, valid send (the sender is monkeypatched), invalid email, missing fields, SMTP connection/auth/send failures, and missing config.
  - No real email is sent in unit tests.
- **Live checks with curl:**
  - Start both services and check that `GET /health` works on both.
  - Check that `GET /` serves the HTML.
  - Send an invalid `/send` and confirm it returns 422.
  - Stop the email service and confirm `/send` returns 503.
- **Real E2E: pause for you.**
  - You copy `email-service/.env.example` to `.env` and fill in the Gmail settings: `smtp.gmail.com`, port 587, your address, and the 16-char App Password.
  - You give me a recipient address.
  - I then send through `POST /send` on :8000, which exercises the full chain.
  - The request from the form uses the same endpoint. I'll verify the page loads, and if a browser tool is available, also click through the form. You confirm the email arrived.
  - I never print `.env` contents.

## Phase 2 (docs) and Phase 7
Before any code, I write `docs/IMPLEMENTATION_PLAN.md` (this plan), `ARCHITECTURE.md` (responsibilities plus a Mermaid diagram), `API.md` (the full contract, status codes and failure scenarios), `SETUP.md` (venvs, `.env` setup, the Gmail App Password note, the run commands) and `TESTING.md`. I also write `README.md` with all 12 requested sections. I then review them against the requirements and update them after implementation wherever the code differs. Service-to-service auth (a shared API key header) is documented as a future improvement.

## Verification
```bash
cd email-service && .venv/bin/pytest -q
cd backend && .venv/bin/pytest -q
# Terminal 1
cd email-service && uvicorn app.main:app --host 127.0.0.1 --port 8001
# Terminal 2
cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000
curl localhost:8000/health
curl localhost:8001/health
# open http://localhost:8000 → send → "✓ Email sent successfully" → email arrives
```

---

## Deviations found during implementation

| Planned | Implemented | Why |
|---|---|---|
| — | `app/errors.py` in both services | One place for the uniform `{success, message, errors?}` body, plus validation and unhandled-error handlers |
| — | `app/utils.py` (`mask_email`) in both services | Recipients are logged masked (`c***@example.com`) |
| — | `backend/app/dependencies.py` | `get_http_client` dependency, so tests can inject `httpx.MockTransport` |
| Email service tests monkeypatch the sender | Tests patch `smtplib.SMTP`/`SMTP_SSL` with a fake class | Exercises the real sender code (STARTTLS, login, error mapping) without any network |
| Duplicated code between services | Intentional | Microservices share no code; each is independently deployable |
| `SMTP_PASSWORD` spaces stripped | Only leading/trailing whitespace is trimmed | Other providers' passwords may contain spaces |
