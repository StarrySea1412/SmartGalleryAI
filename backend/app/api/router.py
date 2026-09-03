from fastapi import APIRouter

from app.api.routes import assets, health, search

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(search.router, tags=["search"])
