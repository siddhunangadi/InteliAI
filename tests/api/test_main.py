from starlette.requests import Request
from starlette.routing import Route

from api.main import _is_frontend_asset


def _request(path: str, route_name: str | None = None) -> Request:
    scope = {"type": "http", "path": path, "headers": []}
    if route_name is not None:
        scope["route"] = Route(path, endpoint=lambda: None, name=route_name)
    return Request(scope)


def test_asset_path_is_frontend_asset():
    assert _is_frontend_asset(_request("/assets/index-abc123.js")) is True


def test_spa_fallback_route_is_frontend_asset():
    assert _is_frontend_asset(_request("/chat", route_name="spa_fallback")) is True


def test_real_api_route_is_not_frontend_asset():
    assert _is_frontend_asset(_request("/documents", route_name="list_documents")) is False


def test_no_route_matched_is_not_frontend_asset():
    """Requests that never resolved to a route (e.g. a 404 before routing
    finished) shouldn't be misclassified as frontend traffic."""
    assert _is_frontend_asset(_request("/nonexistent")) is False
