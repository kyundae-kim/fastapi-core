from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from fastapi_core.core.config import LangfuseConfig
from fastapi_core.core.langfuse import check_langfuse_connection, get_langfuse_client


class TestGetLangfuseClient:
    def test_initializes_singleton_and_returns_registered_client(self):
        config = LangfuseConfig(
            public_key="pk-test",
            secret_key="sk-test",
            host="http://localhost:3000",
        )
        singleton_client = MagicMock()

        with (
            patch(
                "fastapi_core.core.langfuse._create_langfuse_client",
                return_value=MagicMock(),
            ) as mock_create,
            patch(
                "fastapi_core.core.langfuse.langfuse_get_client",
                return_value=singleton_client,
            ) as mock_get_client,
        ):
            client = get_langfuse_client(config)

        mock_create.assert_called_once_with(config)
        mock_get_client.assert_called_once_with(public_key="pk-test")
        assert client is singleton_client

    def test_returns_default_singleton_without_explicit_config(self):
        singleton_client = MagicMock()

        with patch(
            "fastapi_core.core.langfuse.langfuse_get_client",
            return_value=singleton_client,
        ) as mock_get_client:
            client = get_langfuse_client()

        mock_get_client.assert_called_once_with()
        assert client is singleton_client


class TestCheckLangfuseConnection:
    def test_returns_true_for_public_health_endpoint(self):
        config = LangfuseConfig(host="http://localhost:3000")
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"status": "OK"}

        with patch("fastapi_core.core.langfuse.httpx.get", return_value=response) as mock_get:
            assert check_langfuse_connection(config) is True

        mock_get.assert_called_once_with(
            "http://localhost:3000/api/public/health",
            timeout=5,
        )

    def test_returns_false_when_health_status_is_not_ok(self):
        config = LangfuseConfig(host="http://localhost:3000")
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"status": "ERROR"}

        with patch("fastapi_core.core.langfuse.httpx.get", return_value=response):
            assert check_langfuse_connection(config) is False

    def test_returns_false_when_request_fails(self):
        config = LangfuseConfig(host="http://localhost:3000")

        with patch(
            "fastapi_core.core.langfuse.httpx.get",
            side_effect=httpx.RequestError("connection refused"),
        ):
            assert check_langfuse_connection(config) is False
