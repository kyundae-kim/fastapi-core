from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi_core.core.config import OllamaConfig
from fastapi_core.core.ollama import create_ollama_client


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
