from __future__ import annotations

import re

from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from fastapi_core import ErrorMapping, register_error_mapper
from fastapi_core.config import AppConfig
from fastapi_core.factory import create_app


def _app():
    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        include_auth_router=False,
    )

    @app.get("/ok")
    async def ok():
        return {"ok": True}

    @app.get("/failure")
    async def failure():
        raise HTTPException(status_code=409, detail="Conflict")

    return app


def test_correlation_id_is_propagated_to_request_and_response():
    app = _app()

    @app.get("/correlation")
    async def correlation(request: Request):
        return {"correlation_id": request.state.correlation_id}

    with TestClient(app) as client:
        response = client.get(
            "/correlation",
            headers={"X-Correlation-ID": "request-123"},
        )

    assert response.status_code == 200
    assert response.json() == {"correlation_id": "request-123"}
    assert response.headers["X-Correlation-ID"] == "request-123"


def test_invalid_correlation_id_is_replaced():
    app = _app()

    with TestClient(app) as client:
        response = client.get(
            "/ok",
            headers={"X-Correlation-ID": "invalid value with spaces"},
        )

    correlation_id = response.headers["X-Correlation-ID"]
    assert correlation_id != "invalid value with spaces"
    assert re.fullmatch(r"[0-9a-f]{32}", correlation_id)


def test_http_errors_use_problem_details_and_mask_sensitive_values():
    app = _app()

    @app.get("/sensitive")
    async def sensitive():
        raise HTTPException(status_code=400, detail="token=secret-value")

    with TestClient(app) as client:
        response = client.get(
            "/sensitive",
            headers={"X-Correlation-ID": "error-123"},
        )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json() == {
        "type": "about:blank",
        "title": "Bad Request",
        "status": 400,
        "detail": "token=***",
        "instance": "/sensitive",
        "correlation_id": "error-123",
    }


def test_nonstandard_http_status_uses_stable_problem_title():
    app = _app()

    @app.get("/nonstandard")
    async def nonstandard():
        raise HTTPException(status_code=499, detail="Client closed request")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/nonstandard")

    assert response.status_code == 499
    assert response.json()["title"] == "HTTP Error"


def test_validation_and_unhandled_errors_use_safe_problem_details():
    app = _app()

    @app.get("/validated")
    async def validated(count: int):
        return {"count": count}

    @app.get("/crash")
    async def crash():
        raise RuntimeError("password=secret-value")

    with TestClient(app, raise_server_exceptions=False) as client:
        validation_response = client.get("/validated?count=invalid")
        crash_response = client.get("/crash")

    assert validation_response.status_code == 422
    assert validation_response.json()["detail"] == "Request validation failed"
    assert validation_response.json()["correlation_id"]
    assert crash_response.status_code == 500
    assert crash_response.json()["detail"] == "Internal Server Error"
    assert "secret-value" not in crash_response.text


def test_custom_error_mapper_uses_the_standard_problem_envelope():
    class DomainError(Exception):
        pass

    app = _app()
    register_error_mapper(
        app,
        DomainError,
        lambda _request, exc: ErrorMapping(
            status_code=502,
            title="Domain service error",
            detail=str(exc),
            type_uri="https://errors.example/domain-service",
        ),
    )

    @app.get("/domain")
    async def domain():
        raise DomainError("token=domain-secret")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/domain")

    assert response.status_code == 502
    assert response.json()["type"] == "https://errors.example/domain-service"
    assert response.json()["title"] == "Domain service error"
    assert response.json()["detail"] == "token=***"


def test_custom_error_mapper_accepts_async_mappers():
    class DomainError(Exception):
        pass

    async def mapper(_request, exc):
        return ErrorMapping(status_code=503, detail=str(exc))

    app = _app()
    register_error_mapper(app, DomainError, mapper)

    @app.get("/async-domain")
    async def async_domain():
        raise DomainError("temporarily unavailable")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/async-domain")

    assert response.status_code == 503
    assert response.json()["detail"] == "temporarily unavailable"
