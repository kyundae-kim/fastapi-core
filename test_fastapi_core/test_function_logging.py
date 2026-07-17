from __future__ import annotations

import ast
from pathlib import Path


_PACKAGE_ROOT = Path(__file__).parents[1] / "fastapi_core"
_EXCLUDED_FUNCTIONS = {("logging.py", "JsonLogFormatter.format")}


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


def test_all_application_functions_use_py_core_log_decorator() -> None:
    missing: list[str] = []

    for path in sorted(_PACKAGE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        relative_path = str(path.relative_to(_PACKAGE_ROOT))
        for function, qualified_name in _function_names(tree):
            if (relative_path, qualified_name) in _EXCLUDED_FUNCTIONS:
                continue
            decorators = {ast.unparse(decorator) for decorator in function.decorator_list}
            if "log_function_boundary()" not in decorators:
                missing.append(f"{relative_path}:{qualified_name}")

    assert missing == []
