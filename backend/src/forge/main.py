from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forge.api.routers import analytics, arena_auth, costs, cp_approvals, cycle_admin, dashboard, forecast, integrations, monthly_mvp, penalties, player_admin, pulse
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
app.include_router(pulse.router, prefix=f"{settings.api_v1_prefix}/pulse")
app.include_router(monthly_mvp.router, prefix=f"{settings.api_v1_prefix}/admin")
app.include_router(penalties.router, prefix=f"{settings.api_v1_prefix}/penalties")
app.include_router(forecast.router, prefix=f"{settings.api_v1_prefix}/forecast")
app.include_router(player_admin.router, prefix=f"{settings.api_v1_prefix}/admin")
app.include_router(costs.router, prefix=f"{settings.api_v1_prefix}/costs")
app.include_router(arena_auth.router, prefix=settings.api_v1_prefix)


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
