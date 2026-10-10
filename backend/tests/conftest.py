import httpx
import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_http_client
from app.main import app


@pytest.fixture
def client():
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture
def email_service():
    """Replace the Email Microservice with an httpx.MockTransport handler.

    Usage: email_service(handler) where handler(request) returns an httpx.Response or raises.
    Returns a list that collects every request the backend made.
    """
    requests: list[httpx.Request] = []

    def install(handler):
        def recording_handler(request: httpx.Request):
            requests.append(request)
            return handler(request)

        mock_client = httpx.AsyncClient(
            transport=httpx.MockTransport(recording_handler), base_url="http://email-service.test"
        )
        app.dependency_overrides[get_http_client] = lambda: mock_client
        return requests

    return install
