from __future__ import annotations

import ollama

from fastapi_core.core.config import OllamaConfig


def create_ollama_client(config: OllamaConfig) -> ollama.Client:
    return ollama.Client(host=config.host, timeout=config.timeout)


def check_ollama_connection(client: ollama.Client) -> bool:
    try:
        client.list()
        return True
    except Exception:
        return False


def list_model_names(client: ollama.Client) -> list[str]:
    response = client.list()
    return [model.model for model in response.models if model.model]


def generate_text(
    client: ollama.Client,
    config: OllamaConfig,
    prompt: str,
    *,
    model: str | None = None,
) -> str:
    response = client.generate(model=model or config.model, prompt=prompt)
    return response.response or ""
