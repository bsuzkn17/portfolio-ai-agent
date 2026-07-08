from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import router
from app import services


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Fail fast: all required credentials must be present before serving traffic
    settings.validate_required()
    print(
        f"[startup] env={settings.APP_ENV}  "
        f"model={settings.OPENROUTER_MODEL}  "
        f"debug={settings.DEBUG}"
    )
    # Self-healing webhook: every cold start (e.g. a Render redeploy) re-points
    # Telegram at TELEGRAM_WEBHOOK_URL, if configured. No-op otherwise.
    await services.register_webhook()
    yield
    print("[shutdown] graceful exit")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="AI Investment Assistant",
        description=(
            "Secure modular backend for AI-driven investment analysis. "
            "Integrates yfinance (market data), OpenRouter free-tier LLM, "
            "Supabase (persistence), and Telegram Bot API."
        ),
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    app.include_router(router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    uvicorn.run("main:app", host=s.APP_HOST, port=s.APP_PORT, reload=s.DEBUG)
