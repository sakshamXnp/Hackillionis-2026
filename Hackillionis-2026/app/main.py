"""FastAPI Payment Rules Engine API - main application entrypoint."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.config import get_settings
from app.database import close_db, init_db
from app.routes import api_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifespan: initialize resources on startup,
    cleanup on shutdown.
    """
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title=settings.app_name,
    description="Production-grade Payment Rules Engine API with async SQLAlchemy 2.0",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "ok"}
