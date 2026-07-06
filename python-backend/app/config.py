from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False
    # Comma-separated list of allowed CORS origins, e.g. "https://app.example.com,https://admin.example.com"
    # Use "*" only in local development; never in production with credentials.
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # OpenRouter
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_DEFAULT_MODEL: str = "openai/gpt-4o"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    def validate_integration(self, name: str, *required_keys: str) -> None:
        """Raise at startup if any required key for an integration is missing."""
        missing = [k for k in required_keys if not getattr(self, k, "")]
        if missing:
            raise RuntimeError(
                f"[{name}] Missing required environment variable(s): {', '.join(missing)}"
            )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
