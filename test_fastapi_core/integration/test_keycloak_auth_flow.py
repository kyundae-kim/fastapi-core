from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def keycloak_only_app(
    integration_app_config_factory,
    integration_app_factory,
    integration_credentials,
):
    del integration_credentials
    config = integration_app_config_factory(
        enabled_services=["keycloak"],
        required_services=["keycloak"],
        token_url="/integration/token",
    )
    return integration_app_factory(config)


@pytest.fixture
def issued_access_token(keycloak_only_app, integration_credentials) -> str:
    payload = {
        "username": integration_credentials["username"],
        "password": integration_credentials["password"],
    }
    if integration_credentials["scope"]:
        payload["scope"] = integration_credentials["scope"]

    with TestClient(keycloak_only_app) as client:
        response = client.post("/token", data=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    return body["access_token"]



def test_token_endpoint_issues_real_keycloak_token(
    keycloak_only_app,
    integration_credentials,
):
    payload = {
        "username": integration_credentials["username"],
        "password": integration_credentials["password"],
    }
    if integration_credentials["scope"]:
        payload["scope"] = integration_credentials["scope"]

    with TestClient(keycloak_only_app) as client:
        response = client.post("/token", data=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert "refresh_token" in body



def test_user_endpoint_returns_live_user_info(keycloak_only_app, issued_access_token):
    with TestClient(keycloak_only_app) as client:
        response = client.get(
            "/user",
            headers={"Authorization": f"Bearer {issued_access_token}"},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["sub"]
    assert body["username"]
    assert isinstance(body["roles"], list)
    assert isinstance(body["scopes"], list)



def test_user_endpoint_returns_401_for_invalid_live_token(
    keycloak_only_app,
    invalid_bearer_token,
):
    with TestClient(keycloak_only_app) as client:
        response = client.get(
            "/user",
            headers={"Authorization": f"Bearer {invalid_bearer_token}"},
        )

    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "Invalid token"
    assert response.headers["WWW-Authenticate"] == "Bearer"



def test_create_app_wires_keycloak_service_client_and_openapi_token_url(keycloak_only_app):
    assert "keycloak" in keycloak_only_app.state.service_clients
    assert keycloak_only_app.state.auth_provider is not None

    security_scheme = keycloak_only_app.openapi()["components"]["securitySchemes"][
        "OAuth2PasswordBearer"
    ]
    assert security_scheme["flows"]["password"]["tokenUrl"] == "/integration/token"
