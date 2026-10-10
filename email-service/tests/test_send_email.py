import pytest

VALID = {"to": "customer@example.com", "subject": "Test Email", "body": "Hello from the Email Microservice"}


def post(client, **overrides):
    payload = {**VALID, **overrides}
    payload = {k: v for k, v in payload.items() if v is not None}
    return client.post("/send-email", json=payload)


# ---------- success ----------

def test_send_email_success(client, fake_smtp):
    fake = fake_smtp()

    response = post(client)

    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "Email sent successfully"}
    [server] = fake.instances
    assert (server.host, server.port, server.timeout) == ("smtp.test.local", 587, 5.0)
    assert server.calls == ["starttls", "login", "send_message", "quit"]
    [message] = server.sent
    assert message["To"] == "customer@example.com"
    assert message["From"] == "sender@test.local"
    assert message["Subject"] == "Test Email"
    assert message.get_content().strip() == "Hello from the Email Microservice"


def test_send_email_ssl_mode_skips_starttls(client, fake_smtp, monkeypatch):
    monkeypatch.setenv("SMTP_USE_SSL", "true")
    monkeypatch.setenv("SMTP_PORT", "465")
    fake = fake_smtp()

    response = post(client)

    assert response.status_code == 200
    [server] = fake.instances
    assert server.port == 465
    assert server.calls == ["login", "send_message", "quit"]


# ---------- validation ----------

def test_invalid_email_rejected(client, fake_smtp):
    fake = fake_smtp()
    response = post(client, to="not-an-email")

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Validation failed"
    assert [e["field"] for e in body["errors"]] == ["to"]
    assert fake.instances == []


@pytest.mark.parametrize("field", ["to", "subject", "body"])
def test_missing_required_field(client, fake_smtp, field):
    fake_smtp()
    payload = {k: v for k, v in VALID.items() if k != field}

    response = client.post("/send-email", json=payload)

    assert response.status_code == 422
    assert field in [e["field"] for e in response.json()["errors"]]


@pytest.mark.parametrize("field", ["subject", "body"])
def test_blank_field_rejected(client, fake_smtp, field):
    fake_smtp()
    response = post(client, **{field: "   "})

    assert response.status_code == 422
    assert [e["field"] for e in response.json()["errors"]] == [field]


def test_subject_with_line_break_rejected(client, fake_smtp):
    fake_smtp()
    response = post(client, subject="Hi\r\nBcc: victim@example.com")

    assert response.status_code == 422
    assert response.json()["errors"][0]["message"] == "Subject must not contain line breaks"


def test_invalid_json_rejected(client):
    response = client.post("/send-email", content="{not json", headers={"Content-Type": "application/json"})

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "body"


# ---------- SMTP failures ----------

@pytest.mark.parametrize(
    "fail_on, status, message",
    [
        ("connect", 503, "Could not connect to email provider"),
        ("disconnect", 503, "Could not connect to email provider"),
        ("login", 502, "Email provider authentication failed"),
        ("send", 502, "Email sending failed"),
        ("recipient", 400, "Recipient address was rejected"),
        ("unexpected", 500, "Internal server error"),
    ],
)
def test_smtp_failures_are_mapped(client, fake_smtp, fail_on, status, message):
    fake_smtp(fail_on=fail_on)

    response = post(client)

    assert response.status_code == status
    assert response.json() == {"success": False, "message": message}


def test_smtp_errors_do_not_leak_details(client, fake_smtp):
    fake_smtp(fail_on="login")
    response = post(client)

    assert "Password" not in response.text
    assert "535" not in response.text


def test_smtp_not_configured(client, fake_smtp, monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "")
    monkeypatch.setenv("SMTP_PASSWORD", "")
    fake = fake_smtp()

    response = post(client)

    assert response.status_code == 500
    assert response.json() == {"success": False, "message": "Email service is not configured"}
    assert fake.instances == []
