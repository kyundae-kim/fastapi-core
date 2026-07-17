from fastapi_core.factory import create_app


def test_create_app_exposes_runtime_as_the_only_service_state(empty_runtime):
    app = create_app(runtime=empty_runtime, include_auth_router=False)

    assert app.state.service_runtime is empty_runtime
    assert not hasattr(app.state, "settings")
    assert not hasattr(app.state, "service_clients")