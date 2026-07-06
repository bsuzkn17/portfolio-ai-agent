"""
Service layer — business logic lives here.

Each service wraps an external integration (OpenRouter, Supabase, Telegram).
Import `get_settings()` for credentials; never access os.environ directly.
"""

import httpx
from fastapi import HTTPException, status
from app.config import get_settings


def _handle_httpx_error(source: str, exc: Exception) -> None:
    """Translate httpx exceptions into consistent FastAPI HTTP responses."""
    if isinstance(exc, httpx.TimeoutException):
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"{source}: request timed out",
        )
    if isinstance(exc, httpx.HTTPStatusError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{source}: upstream returned {exc.response.status_code}",
        )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"{source}: {str(exc)}",
    )


# ---------------------------------------------------------------------------
# OpenRouter
# ---------------------------------------------------------------------------

async def chat_completion(
    messages: list[dict],
    model: str | None = None,
) -> dict:
    """
    Send a chat-completion request to OpenRouter.

    Args:
        messages: List of {"role": ..., "content": ...} dicts.
        model: Override the default model from settings.

    Returns:
        Raw OpenRouter response dict.
    """
    settings = get_settings()
    chosen_model = model or settings.OPENROUTER_DEFAULT_MODEL

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": chosen_model,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
    except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as exc:
        _handle_httpx_error("OpenRouter", exc)


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

async def send_telegram_message(chat_id: int | str, text: str) -> dict:
    """
    Send a message via the Telegram Bot API.

    Args:
        chat_id: Telegram chat or user ID.
        text: Message text.

    Returns:
        Telegram API response dict.
    """
    settings = get_settings()
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={"chat_id": chat_id, "text": text},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
    except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as exc:
        _handle_httpx_error("Telegram", exc)
