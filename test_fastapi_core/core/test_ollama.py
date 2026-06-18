from unittest.mock import MagicMock, patch

from fastapi_core.core.config import OllamaConfig
from fastapi_core.core.ollama import (
    check_ollama_connection,
    create_ollama_client,
    generate_text,
    list_model_names,
)


def test_create_ollama_client_uses_host_and_timeout_from_config():
    config = OllamaConfig(host="http://localhost:11434", timeout=12.5)
    mock_client = MagicMock()

    with patch("fastapi_core.core.ollama.ollama.Client", return_value=mock_client) as mock_cls:
        client = create_ollama_client(config)

    mock_cls.assert_called_once_with(host="http://localhost:11434", timeout=12.5)
    assert client is mock_client


def test_check_ollama_connection_returns_true_when_list_succeeds():
    mock_client = MagicMock()
    mock_client.list.return_value = MagicMock(models=[])

    assert check_ollama_connection(mock_client) is True



def test_check_ollama_connection_returns_false_on_error():
    mock_client = MagicMock()
    mock_client.list.side_effect = RuntimeError("ollama down")

    assert check_ollama_connection(mock_client) is False



def test_list_model_names_returns_model_names_from_sdk_response():
    model_a = MagicMock(model="llama3.2")
    model_a.model = "llama3.2"
    model_b = MagicMock(model="nomic-embed-text")
    model_b.model = "nomic-embed-text"
    mock_client = MagicMock()
    mock_client.list.return_value = MagicMock(models=[model_a, model_b])

    assert list_model_names(mock_client) == ["llama3.2", "nomic-embed-text"]



def test_generate_text_uses_default_model_from_config_and_returns_response_text():
    config = OllamaConfig(model="llama3.2")
    mock_client = MagicMock()
    mock_client.generate.return_value = MagicMock(response="hello world")

    text = generate_text(mock_client, config, "Say hi")

    assert text == "hello world"
    mock_client.generate.assert_called_once_with(model="llama3.2", prompt="Say hi")



def test_generate_text_allows_overriding_model():
    config = OllamaConfig(model="llama3.2")
    mock_client = MagicMock()
    mock_client.generate.return_value = MagicMock(response="embedding-ready")

    text = generate_text(mock_client, config, "Summarize", model="qwen2.5")

    assert text == "embedding-ready"
    mock_client.generate.assert_called_once_with(model="qwen2.5", prompt="Summarize")
