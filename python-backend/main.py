from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup validation and shutdown logic."""
    settings = get_settings()
    print(f"[startup] env={settings.APP_ENV} debug={settings.DEBUG}")

    # Fail fast: verify required integration credentials are present.
    # Comment out any block if the integration is not yet configured.
    if settings.OPENROUTER_API_KEY:
        settings.validate_integration("OpenRouter", "OPENROUTER_API_KEY")
    if settings.SUPABASE_URL or settings.SUPABASE_ANON_KEY:
        settings.validate_integration("Supabase", "SUPABASE_URL", "SUPABASE_ANON_KEY")
    if settings.TELEGRAM_BOT_TOKEN:
        settings.validate_integration("Telegram", "TELEGRAM_BOT_TOKEN")

    yield
    print("[shutdown] cleaning up")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="AI Investment Assistant",
        description="FastAPI backend for the AI Investment Assistant service.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    app.include_router(router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )
