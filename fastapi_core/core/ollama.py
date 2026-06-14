from __future__ import annotations

import ollama

from fastapi_core.core.config import OllamaConfig


def create_ollama_client(config: OllamaConfig) -> ollama.Client:
    return ollama.Client(host=config.host, timeout=config.timeout)
