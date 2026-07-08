from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # ── OpenRouter (free tier) ───────────────────────────────────────────────
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    # Free model – override via env to swap without code changes
    OPENROUTER_MODEL: str = "google/gemini-2.5-flash:free"

    # ── Supabase ─────────────────────────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # ── Telegram ─────────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    # Optional shared secret set when registering the webhook with Telegram
    # (X-Telegram-Bot-Api-Secret-Token header). Leave blank to skip validation.
    TELEGRAM_WEBHOOK_SECRET: str = ""
    # Full public HTTPS URL of this service's webhook endpoint, e.g.
    # https://portfolio-ai-agent-1.onrender.com/webhook/telegram
    # When set, the app automatically (re-)registers this URL with Telegram
    # on every startup — so a Render redeploy always keeps the webhook current.
    TELEGRAM_WEBHOOK_URL: str = ""

    # ── Derived helpers ───────────────────────────────────────────────────────
    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    def validate_required(self) -> None:
        """Raise at startup if a required credential is absent."""
        required = {
            "OPENROUTER_API_KEY": self.OPENROUTER_API_KEY,
            "SUPABASE_URL": self.SUPABASE_URL,
            "SUPABASE_ANON_KEY": self.SUPABASE_ANON_KEY,
            "TELEGRAM_BOT_TOKEN": self.TELEGRAM_BOT_TOKEN,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise RuntimeError(
                f"Missing required environment variable(s): {', '.join(missing)}"
            )

        # In production, an unauthenticated webhook is a security risk.
        # Enforce TELEGRAM_WEBHOOK_SECRET when APP_ENV is not development.
        if self.APP_ENV != "development" and not self.TELEGRAM_WEBHOOK_SECRET:
            raise RuntimeError(
                "TELEGRAM_WEBHOOK_SECRET must be set in non-development environments. "
                "Register it with Telegram when calling setWebhook."
            )

        # Warn (don't hard-fail) in development so local testing stays easy.
        if self.APP_ENV == "development" and not self.TELEGRAM_WEBHOOK_SECRET:
            import warnings
            warnings.warn(
                "TELEGRAM_WEBHOOK_SECRET is not set. "
                "Webhook endpoint is unauthenticated — acceptable in dev, required in production.",
                stacklevel=2,
            )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
