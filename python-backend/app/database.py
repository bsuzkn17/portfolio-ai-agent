from supabase import create_client, Client
from app.config import get_settings

_supabase_client: Client | None = None


def get_supabase() -> Client:
    """
    Returns a singleton Supabase client.
    Lazily initialised on first call.
    """
    global _supabase_client

    if _supabase_client is None:
        settings = get_settings()

        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env"
            )

        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY,
        )

    return _supabase_client
