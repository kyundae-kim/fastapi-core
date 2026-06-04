from __future__ import annotations

from typing import Any

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


def _get_field(value: Any, *names: str) -> Any:
    if isinstance(value, dict):
        for name in names:
            if name in value and value[name] is not None:
                return value[name]
        return None

    for name in names:
        field = getattr(value, name, None)
        if field is not None:
            return field
    return None


def list_model_names(client: ollama.Client) -> list[str]:
    response = client.list()
    models = _get_field(response, "models") or []
    names: list[str] = []
    for model in models:
        name = _get_field(model, "model", "name")
        if name is not None:
            names.append(str(name))
    return names


def generate_text(client: ollama.Client, *, model: str, prompt: str) -> str:
    response = client.generate(model=model, prompt=prompt)
    text = _get_field(response, "response")
    if text is None:
        raise ValueError("Ollama generate response field missing")
    return str(text)
