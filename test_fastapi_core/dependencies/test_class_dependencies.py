from __future__ import annotations

import importlib
import inspect
import pkgutil

import fastapi_core.dependencies as dependencies_package


def test_no_get_dependencies_are_callable_class_instances():
    dependency_class_names: list[str] = []

    for module_info in pkgutil.iter_modules(dependencies_package.__path__):
        module = importlib.import_module(
            f"{dependencies_package.__name__}.{module_info.name}"
        )
        dependency_class_names.extend(
            name
            for name, value in vars(module).items()
            if name.startswith("Get")
            and name.endswith("Dependency")
            and inspect.isclass(value)
        )

    assert dependency_class_names == []
