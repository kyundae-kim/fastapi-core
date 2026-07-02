from fastapi_core.dependencies.auth import get_auth_provider, get_current_user, require_permissions
from fastapi_core.dependencies.config import get_config, get_settings
from fastapi_core.dependencies.services import get_service_client

__all__ = [
    "get_auth_provider",
    "get_config",
    "get_current_user",
    "get_service_client",
    "get_settings",
    "require_permissions",
]
