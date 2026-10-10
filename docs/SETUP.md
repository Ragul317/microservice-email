# Setup

## Requirements
- Python 3.10+ (developed with 3.12) with `venv` and `pip`
- An SMTP account. Gmail with an App Password is used in this guide.
- No Node.js, Docker or database is needed.

## 1. Create one virtual environment per service

Each service is independent and has its own virtualenv.

```bash
# Email Microservice
cd email-service
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
deactivate
cd ..

# Main Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..
```

## 2. Configure environment variables

Copy each `.env.example` to `.env` and edit it:

```bash
cp email-service/.env.example email-service/.env
cp backend/.env.example backend/.env
```

**Never commit `.env`.** It is listed in `.gitignore`. Only `.env.example` (placeholders) is committed.

### `email-service/.env`

| Variable | Example | Meaning |
|---|---|---|
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | `587` | 587 = STARTTLS, 465 = SSL |
| `SMTP_USERNAME` | `you@gmail.com` | SMTP login |
| `SMTP_PASSWORD` | `abcdefghijklmnop` | SMTP password or App Password |
| `SMTP_FROM` | `you@gmail.com` | From address (Gmail requires your own address or a verified alias) |
| `SMTP_USE_SSL` | `false` | `true` for implicit SSL on port 465 |
| `SMTP_TIMEOUT` | `10` | Seconds to wait for the SMTP server |
| `LOG_LEVEL` | `INFO` | Logging level |

### `backend/.env`

| Variable | Example | Meaning |
|---|---|---|
| `EMAIL_SERVICE_URL` | `http://localhost:8001` | Base URL of the Email Microservice |
| `EMAIL_SERVICE_TIMEOUT` | `20` | Seconds. Keep this larger than `SMTP_TIMEOUT` |
| `CORS_ORIGINS` | `http://localhost:8000,http://127.0.0.1:8000` | Comma-separated allowed browser origins |
| `LOG_LEVEL` | `INFO` | Logging level |

### Gmail App Password
Gmail rejects your normal account password over SMTP when 2-Step Verification is on, which is the common case. You then need an **App Password**:

1. Turn on 2-Step Verification for the Google account.
2. Go to <https://myaccount.google.com/apppasswords>, create an app password (any name), and copy the 16 characters.
3. Put it in `SMTP_PASSWORD`. Spaces are fine to remove.

Workspace accounts may have App Passwords disabled by an administrator. In that case, use another SMTP provider.

## 3. Run

Terminal 1 (Email Microservice):
```bash
cd email-service
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Terminal 2 (Main Backend + frontend):
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://localhost:8000**, fill in the form, and click **Send Email**.

Quick check:
```bash
curl http://localhost:8000/health   # {"status":"healthy"}
curl http://localhost:8001/health   # {"status":"healthy"}
```

## Common errors

| Symptom | Cause / fix |
|---|---|
| "Email service is unavailable" | The Email Microservice isn't running on `EMAIL_SERVICE_URL`. Start Terminal 1. |
| "Email provider authentication failed" | Wrong `SMTP_USERNAME` or `SMTP_PASSWORD`. For Gmail, use an App Password. |
| "Email service is not configured" | `email-service/.env` is missing or has empty SMTP values. |
| "Could not connect to email provider" | Wrong host or port, the SSL/STARTTLS setting doesn't match the port, or a firewall is blocking outbound SMTP. |
| "Backend unavailable" in the page | The Main Backend isn't running on :8000. |
| `ModuleNotFoundError: app` | Run uvicorn from inside `backend/` or `email-service/`. |
| `Address already in use` | Another process is using 8000 or 8001. Stop it or change `--port` (and `EMAIL_SERVICE_URL`). |
