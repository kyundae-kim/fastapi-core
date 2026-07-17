from __future__ import annotations

import warnings

from docmesh_py_core import ServiceRuntime


def test_integration_app_factory_uses_runtime_injection_without_deprecated_settings(
    integration_app_config_factory,
    integration_app_factory,
):
    config = integration_app_config_factory(
        enabled_services=[],
        required_services=[],
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        app = integration_app_factory(config, include_auth_router=False)

    assert isinstance(app.state.service_runtime, ServiceRuntime)
    assert app.state.settings is app.state.service_runtime.configs
    assert app.state.service_clients is app.state.service_runtime.clients
