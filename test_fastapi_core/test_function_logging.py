from __future__ import annotations

import ast
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from fastapi_core.function_logging import log_function_boundary


_PACKAGE_ROOT = Path(__file__).parents[1] / "fastapi_core"
_EXCLUDED_MODULES = {"function_logging.py"}
_EXCLUDED_FUNCTIONS = {
    ("logging.py", "JsonLogFormatter.format"),
    ("http.py", "AccessLogMiddleware.__call__"),
    ("http.py", "AccessLogMiddleware.__call__.send_with_access_log"),
    ("http.py", "CorrelationIdMiddleware.__call__"),
    ("http.py", "CorrelationIdMiddleware.__call__.send_with_correlation_id"),
}


def _function_names(tree: ast.AST) -> list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str]]:
    functions: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str]] = []

    def visit(node: ast.AST, parents: tuple[str, ...] = ()) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                visit(child, (*parents, child.name))
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualified_name = ".".join((*parents, child.name))
                functions.append((child, qualified_name))
                visit(child, (*parents, child.name))
            else:
                visit(child, parents)

    visit(tree)
    return functions


def test_all_application_functions_use_local_log_decorator() -> None:
    missing: list[str] = []

    for path in sorted(_PACKAGE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        relative_path = str(path.relative_to(_PACKAGE_ROOT))
        if relative_path in _EXCLUDED_MODULES:
            continue
        for function, qualified_name in _function_names(tree):
            if (relative_path, qualified_name) in _EXCLUDED_FUNCTIONS:
                continue
            decorators = {ast.unparse(decorator) for decorator in function.decorator_list}
            if "log_function_boundary()" not in decorators:
                missing.append(f"{relative_path}:{qualified_name}")

    assert missing == []


def test_log_function_boundary_preserves_sync_result_and_emits_boundaries(caplog):
    @log_function_boundary("sync-example")
    def example(value: int) -> int:
        return value + 1

    with caplog.at_level(logging.INFO):
        result = example(1)

    assert result == 2
    records = [record for record in caplog.records if record.function_event == "sync-example"]
    assert [record.getMessage() for record in records] == [
        "function_start",
        "function_end",
    ]


@pytest.mark.asyncio
async def test_log_function_boundary_preserves_async_error_and_logs_it(caplog):
    @log_function_boundary("async-example")
    async def example() -> None:
        raise RuntimeError("expected failure")

    with caplog.at_level(logging.INFO), pytest.raises(RuntimeError, match="expected failure"):
        await example()

    records = [record for record in caplog.records if record.function_event == "async-example"]
    assert [record.getMessage() for record in records] == [
        "function_start",
        "function_error",
    ]
    assert records[-1].exc_info is not None


def test_log_function_boundary_skips_info_calls_when_info_is_disabled(caplog):
    logger = logging.getLogger(__name__)

    @log_function_boundary("disabled-info-example")
    def example() -> str:
        return "result"

    with (
        caplog.at_level(logging.WARNING, logger=__name__),
        patch.object(logger, "info") as info,
    ):
        assert example() == "result"

    info.assert_not_called()


def test_log_function_boundary_still_logs_errors_when_info_is_disabled(caplog):
    @log_function_boundary("disabled-info-error-example")
    def example() -> None:
        raise RuntimeError("expected failure")

    with (
        caplog.at_level(logging.WARNING, logger=__name__),
        pytest.raises(RuntimeError, match="expected failure"),
    ):
        example()

    records = [
        record
        for record in caplog.records
        if record.function_event == "disabled-info-error-example"
    ]
    assert [record.getMessage() for record in records] == ["function_error"]
    assert records[0].exc_info is not None


def test_log_function_boundary_observes_level_changes_during_call(caplog):
    logger = logging.getLogger(__name__)

    @log_function_boundary("dynamic-level-example")
    def example() -> None:
        logger.setLevel(logging.INFO)

    original_level = logger.level
    try:
        logger.setLevel(logging.WARNING)
        with caplog.at_level(logging.INFO, logger=""):
            example()
    finally:
        logger.setLevel(original_level)

    records = [
        record
        for record in caplog.records
        if record.function_event == "dynamic-level-example"
    ]
    assert [record.getMessage() for record in records] == ["function_end"]
