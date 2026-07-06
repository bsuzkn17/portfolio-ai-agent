"""
routes.py — FastAPI route definitions.

Endpoints:
  GET  /                   Health check
  POST /webhook/telegram   Telegram Bot webhook receiver

Telegram command handled:
  /analyze {TICKER}
    1. Fetch sanitized market data via yfinance
    2. Load user portfolio context from Supabase
    3. Build anonymous prompt (no PII, no absolute amounts)
    4. Call OpenRouter LLM for multi-point investment analysis
    5. Persist result to Supabase analysis_logs
    6. Dispatch response via Telegram Bot API
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.config import get_settings
from app import database as db
from app import services

log = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/", tags=["Health"])
async def health_check() -> dict:
    """Simple liveness probe."""
    return {"status": "running"}


# ─────────────────────────────────────────────────────────────────────────────
# Telegram webhook
# ─────────────────────────────────────────────────────────────────────────────

def _validate_webhook_secret(secret_header: str | None) -> None:
    """
    If TELEGRAM_WEBHOOK_SECRET is configured, verify the request header.
    Raises 403 on mismatch. Skips validation when the secret is not set.
    """
    configured = get_settings().TELEGRAM_WEBHOOK_SECRET
    if not configured:
        return
    if secret_header != configured:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook secret.",
        )


def _parse_command(text: str | None) -> tuple[str, str] | None:
    """
    Parse a Telegram command string.
    Strips bot-name suffix (e.g. /analyze@MyBot AAPL → ("analyze", "AAPL")).
    Returns (command, argument) or None if text is not a command.
    """
    if not text or not text.startswith("/"):
        return None
    parts = text.strip().split()
    raw_cmd = parts[0].lstrip("/").lower()
    # Handle /command@BotName format
    cmd = raw_cmd.split("@")[0]
    arg = parts[1].upper() if len(parts) > 1 else ""
    return cmd, arg


async def _handle_analyze(
    chat_id: int,
    user_id: str,
    ticker: str,
) -> None:
    """
    Full /analyze pipeline. Designed to run as a background task so Telegram
    does not time-out the webhook before the LLM responds.
    """
    if not ticker:
        await services.send_telegram_message(
            chat_id,
            "⚠️ Usage: <code>/analyze TICKER</code>\nExample: <code>/analyze AAPL</code>",
        )
        return

    # 1. Acknowledge immediately
    await services.send_telegram_message(
        chat_id,
        f"🔍 Analysing <b>{ticker}</b> — fetching market data and running AI model…",
    )

    # 2. Fetch market data + portfolio context concurrently.
    #    All three tasks are gathered together so that a failure in any one
    #    cancels the others and does not leave orphaned asyncio tasks.
    market_data_coro = services.fetch_market_data(ticker)
    portfolio_coro = db.get_portfolio_entry(user_id, ticker)
    recent_coro = db.get_recent_analyses(user_id, ticker, limit=1)

    try:
        market_data, portfolio_entry, recent_analyses = await asyncio.gather(
            market_data_coro, portfolio_coro, recent_coro
        )
    except ValueError as exc:
        # User-visible error: bad ticker symbol — safe to surface
        await services.send_telegram_message(chat_id, f"❌ {exc}")
        return
    except Exception:
        # Internal error: log detail, send generic message to user
        log.exception("Data fetch failed for ticker=%s user=%s", ticker, user_id)
        await services.send_telegram_message(
            chat_id, "❌ Failed to fetch market data. Please try again later."
        )
        return

    # 3. Extract current price (used only as denominator for % calculations;
    #    the raw value is never forwarded to the LLM).
    try:
        import yfinance as yf
        loop = asyncio.get_event_loop()
        current_price = await loop.run_in_executor(
            None, lambda: float(yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1])
        )
    except Exception:
        current_price = None

    # 4. Build anonymised prompt context (no absolute amounts, no PII)
    prompt_context = services.build_prompt_context(
        market_data=market_data,
        portfolio_entry=portfolio_entry,
        recent_analyses=recent_analyses,
        current_price=current_price,
    )

    # 5. Query LLM
    try:
        ai_response = await services.chat_completion(prompt_context)
    except Exception as exc:
        log.exception("LLM call failed for ticker=%s", ticker)
        await services.send_telegram_message(
            chat_id, f"❌ AI analysis failed: {exc}"
        )
        return

    # 6. Persist to Supabase (fire-and-forget style — don't block Telegram reply)
    async def _persist():
        try:
            await db.save_analysis_log(
                user_id=user_id,
                ticker=ticker,
                prompt_context=prompt_context,
                ai_response=ai_response,
            )
        except Exception:
            log.exception("Failed to persist analysis log ticker=%s user=%s", ticker, user_id)

    asyncio.create_task(_persist())

    # 7. Send AI response to Telegram
    header = f"📊 <b>Investment Analysis — {ticker}</b>\n{'─' * 36}\n\n"
    await services.send_telegram_message(chat_id, header + ai_response)


@router.post("/webhook/telegram", status_code=status.HTTP_200_OK, tags=["Telegram"])
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    """
    Receive and dispatch Telegram Bot webhook updates.

    Security:
    - Optional shared-secret header validation (set TELEGRAM_WEBHOOK_SECRET).
    - Returns HTTP 200 immediately for all valid payloads to satisfy Telegram's
      delivery contract; the heavy work runs as a background asyncio task.
    """
    _validate_webhook_secret(x_telegram_bot_api_secret_token)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload."
        )

    message = body.get("message") or body.get("edited_message")
    if not message:
        return {"ok": True}  # Telegram sends non-message updates (polls, callbacks, etc.)

    chat_id: int = message.get("chat", {}).get("id")
    from_user: dict = message.get("from") or {}
    # Use Telegram user ID as the anonymous internal identifier
    user_id: str = str(from_user.get("id", chat_id))
    text: str | None = message.get("text")

    if not chat_id:
        return {"ok": True}

    parsed = _parse_command(text)
    if parsed is None:
        return {"ok": True}  # Ignore non-command messages

    cmd, arg = parsed

    if cmd == "analyze":
        # Dispatch as background task — webhook must return within Telegram's timeout
        asyncio.create_task(_handle_analyze(chat_id=chat_id, user_id=user_id, ticker=arg))

    elif cmd == "start" or cmd == "help":
        asyncio.create_task(
            services.send_telegram_message(
                chat_id,
                (
                    "👋 <b>AI Investment Assistant</b>\n\n"
                    "Available commands:\n"
                    "• <code>/analyze TICKER</code> — full multi-point analysis\n"
                    "  Example: <code>/analyze TSLA</code>\n\n"
                    "Analysis includes: technical metrics, fundamental ratios, "
                    "entry/target/stop zones, risk &amp; confidence scores."
                ),
            )
        )

    return {"ok": True}
