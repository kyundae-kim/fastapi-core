from __future__ import annotations

import json
import logging

from docmesh_py_core import configure_logging
from fastapi_core.function_logging import log_function_boundary

from fastapi_core.config import AppConfig


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        function_event = getattr(record, "function_event", None)
        if function_event not in (None, "-"):
            payload["function_event"] = function_event
        event = getattr(record, "event", None)
        if event is not None:
            payload["event"] = event
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


@log_function_boundary()
def configure_application_logging(config: AppConfig) -> logging.Logger:
    root_logger = configure_logging(
        level=config.log_level,
        log_path=config.log_path,
        force=config.log_force,
    )
    if config.log_json:
        formatter = JsonLogFormatter()
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)
    return root_logger


__all__ = ["JsonLogFormatter", "configure_application_logging"]
