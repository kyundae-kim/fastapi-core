from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from fastapi_core.core.config import OllamaConfig
from fastapi_core.core.ollama import (
    check_ollama_connection,
    create_ollama_client,
    generate_text,
    list_model_names,
)


class TestOllamaConfig:
    def test_default_values(self):
        cfg = OllamaConfig()
        assert cfg.host == "http://ollama:11434"
        assert cfg.model == "llama3.2"
        assert cfg.timeout == 60.0


class TestCreateOllamaClient:
    def test_uses_host_and_timeout_from_config(self):
        cfg = OllamaConfig(host="http://localhost:11434", model="qwen3:latest", timeout=15.5)
        mock_client = MagicMock()

        with patch("fastapi_core.core.ollama.ollama.Client", return_value=mock_client) as mock_cls:
            client = create_ollama_client(cfg)

        mock_cls.assert_called_once_with(host="http://localhost:11434", timeout=15.5)
        assert client is mock_client


class TestCheckOllamaConnection:
    def test_returns_true_when_list_succeeds(self):
        mock_client = MagicMock()
        mock_client.list.return_value = {"models": []}

        assert check_ollama_connection(mock_client) is True
        mock_client.list.assert_called_once_with()

    def test_returns_false_when_list_raises(self):
        mock_client = MagicMock()
        mock_client.list.side_effect = RuntimeError("connection error")

        assert check_ollama_connection(mock_client) is False


class TestListModelNames:
    def test_extracts_names_from_models_attribute(self):
        mock_client = MagicMock()
        mock_client.list.return_value = SimpleNamespace(
            models=[
                SimpleNamespace(model="llama3.2:latest"),
                SimpleNamespace(model="qwen3:latest"),
            ]
        )

        assert list_model_names(mock_client) == ["llama3.2:latest", "qwen3:latest"]

    def test_extracts_names_from_dict_response(self):
        mock_client = MagicMock()
        mock_client.list.return_value = {
            "models": [
                {"model": "llama3.2:latest"},
                {"name": "qwen3:latest"},
            ]
        }

        assert list_model_names(mock_client) == ["llama3.2:latest", "qwen3:latest"]


class TestGenerateText:
    def test_returns_generated_text(self):
        mock_client = MagicMock()
        mock_client.generate.return_value = {"response": "안녕하세요"}

        result = generate_text(mock_client, model="llama3.2", prompt="hello")

        mock_client.generate.assert_called_once_with(model="llama3.2", prompt="hello")
        assert result == "안녕하세요"

    def test_raises_when_response_field_missing(self):
        mock_client = MagicMock()
        mock_client.generate.return_value = {"done": True}

        with pytest.raises(ValueError, match="response field"):
            generate_text(mock_client, model="llama3.2", prompt="hello")
