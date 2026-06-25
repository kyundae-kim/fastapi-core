from fastapi_core.routers.auth import router as auth_router
from fastapi_core.routers.health import router as health_router

__all__ = ["auth_router", "health_router"]
