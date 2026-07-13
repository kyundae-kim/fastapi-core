from __future__ import annotations

import fastapi_core.schemas as schemas_module

from fastapi_core.schemas.health import HealthResponse, HealthServiceDetail
from fastapi_core.schemas.token import TokenResponse
from fastapi_core.schemas.user import UserInfo


def test_token_response_defaults_to_bearer():
    model = TokenResponse(access_token="token")

    assert model.refresh_token is None
    assert model.token_type == "bearer"


def test_schema_package_exports_problem_detail():
    assert "ProblemDetail" in dir(schemas_module)


def test_user_info_defaults_roles_and_scopes_to_empty_lists():
    model = UserInfo(sub="user-1", username="alice")

    assert model.roles == []
    assert model.scopes == []


def test_health_response_requires_status():
    model = HealthResponse(status="ok")

    assert model.status == "ok"
    assert model.details is None


def test_health_response_parses_explicit_service_details():
    model = HealthResponse(
        status="degraded",
        details={
            "nats": HealthServiceDetail(
                ok=False,
                error="nats unavailable",
                required=False,
                enabled=True,
            )
        },
    )

    assert model.details is not None
    assert model.details["nats"].ok is False
    assert model.details["nats"].required is False
    assert model.details["nats"].enabled is True
