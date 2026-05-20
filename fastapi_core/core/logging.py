import logging as _logging
from typing import Literal


def setup_logging(level: Literal["WARNING", "INFO", "DEBUG"] = "DEBUG") -> None:
    log_level = getattr(_logging, level, _logging.DEBUG)
    _logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    _logging.getLogger().setLevel(log_level)
