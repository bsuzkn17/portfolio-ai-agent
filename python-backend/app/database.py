"""
database.py — Supabase persistence layer.

Tables required (run supabase/schema.sql once against your project):

  portfolio_memory  – per-user, per-ticker position metadata
  analysis_logs     – immutable audit trail of every AI analysis run

All Supabase calls are synchronous (supabase-py v2 does not expose async).
They are wrapped in asyncio.get_event_loop().run_in_executor so they never
block the FastAPI event loop.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from supabase import Client, create_client

from app.config import get_settings

log = logging.getLogger(__name__)

# ── Singleton ─────────────────────────────────────────────────────────────────

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        s = get_settings()
        if not s.SUPABASE_URL or not s.SUPABASE_ANON_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment."
            )
        _client = create_client(s.SUPABASE_URL, s.SUPABASE_ANON_KEY)
    return _client


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _run(fn) -> Any:
    """Run a blocking Supabase call in a thread-pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fn)


# ── Portfolio memory ──────────────────────────────────────────────────────────

async def get_portfolio_entry(user_id: str, ticker: str) -> dict | None:
    """
    Retrieve a single portfolio position for (user_id, ticker).

    Returns the row dict or None if not found.
    Stored fields: relative_weight, entry_cost, target_price, stop_loss.
    Absolute financial amounts stay in the database and are NEVER forwarded
    to the LLM verbatim – routes.py converts them to relative percentages.
    """
    def _fetch():
        result = (
            get_supabase()
            .table("portfolio_memory")
            .select("*")
            .eq("user_id", user_id)
            .eq("ticker", ticker.upper())
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    try:
        return await _run(_fetch)
    except Exception as exc:
        log.error("get_portfolio_entry failed: %s", exc)
        return None


async def upsert_portfolio_entry(
    *,
    user_id: str,
    ticker: str,
    relative_weight: float,
    entry_cost: float,
    target_price: float,
    stop_loss: float,
) -> None:
    """
    Insert or update a portfolio position. Uses ON CONFLICT(user_id, ticker)
    to overwrite existing rows so data stays current.
    """
    payload = {
        "user_id": user_id,
        "ticker": ticker.upper(),
        "relative_weight": round(relative_weight, 4),
        "entry_cost": round(entry_cost, 4),
        "target_price": round(target_price, 4),
        "stop_loss": round(stop_loss, 4),
    }

    def _upsert():
        get_supabase().table("portfolio_memory").upsert(
            payload, on_conflict="user_id,ticker"
        ).execute()

    try:
        await _run(_upsert)
    except Exception as exc:
        log.error("upsert_portfolio_entry failed: %s", exc)
        raise


# ── Analysis logs ─────────────────────────────────────────────────────────────

async def save_analysis_log(
    *,
    user_id: str,
    ticker: str,
    prompt_context: str,
    ai_response: str,
) -> None:
    """
    Persist an immutable record of every AI analysis run.
    prompt_context contains the sanitized (non-PII) data fed to the model.
    """
    payload = {
        "user_id": user_id,
        "ticker": ticker.upper(),
        "prompt_context": prompt_context,
        "ai_response": ai_response,
    }

    def _insert():
        get_supabase().table("analysis_logs").insert(payload).execute()

    try:
        await _run(_insert)
    except Exception as exc:
        log.error("save_analysis_log failed: %s", exc)
        raise


async def get_recent_analyses(
    user_id: str,
    ticker: str,
    limit: int = 3,
) -> list[dict]:
    """
    Retrieve the most recent AI analysis responses for (user_id, ticker).
    Used to give the model a short prior-thesis context window.
    Only ai_response and created_at are fetched – prompt_context is excluded
    from the context injection to keep token usage low.
    """
    def _fetch():
        result = (
            get_supabase()
            .table("analysis_logs")
            .select("ai_response, created_at")
            .eq("user_id", user_id)
            .eq("ticker", ticker.upper())
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    try:
        return await _run(_fetch)
    except Exception as exc:
        log.error("get_recent_analyses failed: %s", exc)
        return []
