import httpx
from fastapi import Request


def get_http_client(request: Request) -> httpx.AsyncClient:
    """The shared client created in the app lifespan. Tests override this dependency."""
    return request.app.state.http_client
