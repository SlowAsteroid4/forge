from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forge.api.routers import analytics, cp_approvals, cycle_admin, dashboard, integrations
from forge.core.config import get_settings
from forge.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events de la app."""
    # Startup
    setup_logging()
    yield
    # Shutdown
    pass


# Crear app
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(integrations.router, prefix=f"{settings.api_v1_prefix}/integrations")
app.include_router(dashboard.router, prefix=f"{settings.api_v1_prefix}/dashboard")
app.include_router(cp_approvals.router, prefix=f"{settings.api_v1_prefix}/cp-approvals")
app.include_router(cycle_admin.router, prefix=f"{settings.api_v1_prefix}/admin")
app.include_router(analytics.router, prefix=f"{settings.api_v1_prefix}/analytics")


@app.get("/")
def root():
    """Health check."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
    }


@app.get("/health")
def health():
    """Health check detallado."""
    return {
        "status": "healthy",
        "environment": settings.app_env,
        "features": {
            "arena": settings.enable_arena,
            "achievements": settings.enable_achievements,
            "shop": settings.enable_shop,
            "forecast": settings.enable_forecast,
        },
    }
