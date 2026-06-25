from __future__ import annotations

from fastapi_core.schemas.health import HealthResponse
from fastapi_core.schemas.token import TokenResponse
from fastapi_core.schemas.user import UserInfo



def test_token_response_defaults_to_bearer():
    model = TokenResponse(access_token="token")

    assert model.refresh_token is None
    assert model.token_type == "bearer"



def test_user_info_defaults_roles_and_scopes_to_empty_lists():
    model = UserInfo(sub="user-1", username="alice")

    assert model.roles == []
    assert model.scopes == []



def test_health_response_requires_status():
    model = HealthResponse(status="ok")

    assert model.status == "ok"
    assert model.details is None
