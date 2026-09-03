from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import init_db

WEB_DIR = Path(__file__).resolve().parents[2] / "web"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.ensure_data_dirs()
    init_db()
    yield


def mount_web_app(app: FastAPI) -> None:
    if not WEB_DIR.exists():
        return

    app.mount("/web", StaticFiles(directory=WEB_DIR), name="web")

    @app.get("/", include_in_schema=False)
    def web_index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/app", include_in_schema=False)
    def web_app() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Local-first intelligent gallery backend.",
        lifespan=lifespan,
    )
    app.include_router(api_router, prefix=settings.api_prefix)
    mount_web_app(app)
    return app


app = create_app()
