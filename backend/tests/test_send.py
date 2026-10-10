import json

import httpx
import pytest

VALID = {"to": "customer@example.com", "subject": "Test Email", "message": "Hello from the application"}


def ok_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"success": True, "message": "Email sent successfully"})


def post(client, payload):
    return client.post("/send", json=payload)


# ---------- success ----------

def test_send_success_calls_email_service(client, email_service):
    calls = email_service(ok_handler)

    response = post(client, VALID)

    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "Email sent successfully"}
    [request] = calls
    assert request.method == "POST"
    assert request.url.path == "/send-email"
    assert json.loads(request.content) == {
        "to": "customer@example.com",
        "subject": "Test Email",
        "body": "Hello from the application",  # message -> body
    }


# ---------- validation (email service must not be called) ----------

@pytest.mark.parametrize(
    "payload, field",
    [
        ({"subject": "Test", "message": "Hi"}, "to"),  # missing email
        ({**VALID, "to": "not-an-email"}, "to"),  # invalid email
        ({**VALID, "to": ""}, "to"),  # empty email
        ({"to": "a@example.com", "message": "Hi"}, "subject"),  # missing subject
        ({**VALID, "subject": "   "}, "subject"),  # blank subject
        ({**VALID, "subject": "Hi\nBcc: x@example.com"}, "subject"),  # header injection
        ({"to": "a@example.com", "subject": "Test"}, "message"),  # missing message
        ({**VALID, "message": ""}, "message"),  # empty message
        ({**VALID, "message": "x" * 10_001}, "message"),  # too long
    ],
)
def test_send_validation_errors(client, email_service, payload, field):
    calls = email_service(ok_handler)

    response = post(client, payload)

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Validation failed"
    assert field in [e["field"] for e in body["errors"]]
    assert calls == []


# ---------- email service failures ----------

def test_email_service_unavailable(client, email_service):
    def handler(request):
        raise httpx.ConnectError("Connection refused", request=request)

    email_service(handler)
    response = post(client, VALID)

    assert response.status_code == 503
    assert response.json() == {
        "success": False,
        "message": "Email service is unavailable. Please try again later.",
    }


def test_email_service_timeout(client, email_service):
    def handler(request):
        raise httpx.ReadTimeout("timed out", request=request)

    email_service(handler)
    response = post(client, VALID)

    assert response.status_code == 504
    assert response.json() == {"success": False, "message": "Email service timed out. Please try again later."}


def test_email_service_error_response_is_forwarded_cleanly(client, email_service):
    email_service(
        lambda request: httpx.Response(502, json={"success": False, "message": "Email provider authentication failed"})
    )

    response = post(client, VALID)

    assert response.status_code == 502
    assert response.json() == {"success": False, "message": "Email provider authentication failed"}


def test_email_service_non_json_response(client, email_service):
    email_service(lambda request: httpx.Response(200, text="<html>proxy error</html>"))

    response = post(client, VALID)

    assert response.status_code == 502
    assert response.json() == {"success": False, "message": "Email sending failed"}


def test_email_service_500_without_body(client, email_service):
    email_service(lambda request: httpx.Response(500))

    response = post(client, VALID)

    assert response.status_code == 502
    assert response.json()["message"] == "Email sending failed"
