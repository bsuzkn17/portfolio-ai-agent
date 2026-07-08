"""
services.py — External integration layer.

Functions:
  fetch_market_data(ticker)        yfinance → sanitized relative metrics dict
  build_prompt_context(...)        assemble anonymous LLM prompt string
  chat_completion(messages)        OpenRouter free-tier LLM call
  send_telegram_message(...)       Telegram Bot API via async httpx

Privacy contract:
  - Absolute price levels, revenue figures, and balance sheet amounts are
    NEVER forwarded to the LLM.  Only normalised ratios and % changes are used.
  - User identity (chat_id, name) is stripped before any AI call.
"""

from __future__ import annotations

import asyncio
import logging
import math
from typing import Any

import httpx
import yfinance as yf

from app.config import get_settings

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Market data — yfinance (free, no API key required)
# ─────────────────────────────────────────────────────────────────────────────

def _safe_pct(numerator: float | None, denominator: float | None) -> float | None:
    """Return (numerator / denominator - 1) * 100, or None on any error."""
    try:
        if numerator is None or denominator is None:
            return None
        if denominator == 0:
            return None
        return round((numerator / denominator - 1) * 100, 2)
    except Exception:
        return None


def _safe_ratio(a: float | None, b: float | None) -> float | None:
    try:
        if a is None or b is None or b == 0:
            return None
        return round(a / b, 4)
    except Exception:
        return None


def _annualised_vol(returns) -> float | None:
    """Annualised daily-return standard deviation as a percentage."""
    try:
        std = float(returns.std())
        return round(std * math.sqrt(252) * 100, 2)
    except Exception:
        return None


def _compute_price_metrics(hist) -> dict:
    """
    Derive relative price metrics from an OHLCV history DataFrame.
    Returns only percentage changes and ratios – no absolute prices.
    """
    metrics: dict[str, Any] = {}
    if hist is None or hist.empty:
        return metrics

    closes = hist["Close"].dropna()
    if len(closes) < 2:
        return metrics

    daily_returns = closes.pct_change().dropna()
    current = float(closes.iloc[-1])

    def _pct_return(n_days: int) -> float | None:
        if len(closes) < n_days + 1:
            return None
        past = float(closes.iloc[-(n_days + 1)])
        return _safe_pct(current, past)

    metrics["return_1d_pct"] = _pct_return(1)
    metrics["return_5d_pct"] = _pct_return(5)
    metrics["return_30d_pct"] = _pct_return(30)
    metrics["return_60d_pct"] = _pct_return(60) if len(closes) >= 61 else None
    metrics["volatility_30d_ann_pct"] = _annualised_vol(daily_returns.tail(30))

    # SMA ratios (price vs moving average, as % deviation)
    for window, label in [(20, "sma20"), (50, "sma50")]:
        if len(closes) >= window:
            sma = float(closes.tail(window).mean())
            metrics[f"price_vs_{label}_pct"] = _safe_pct(current, sma)

    # Volume ratio: recent 5-day avg vs 30-day avg
    if "Volume" in hist.columns:
        vols = hist["Volume"].dropna()
        if len(vols) >= 30:
            recent_vol = float(vols.tail(5).mean())
            base_vol = float(vols.tail(30).mean())
            metrics["volume_ratio_5d_vs_30d"] = _safe_ratio(recent_vol, base_vol)

    return metrics


def _compute_fundamental_metrics(info: dict, balance_sheet, financials) -> dict:
    """
    Extract only normalised fundamental ratios from yfinance data.
    Absolute monetary amounts (revenue, assets, debt) are never included.
    """
    metrics: dict[str, Any] = {}

    # Valuation multiples (already ratios)
    for key in ("trailingPE", "forwardPE", "priceToBook", "enterpriseToEbitda"):
        val = info.get(key)
        if val is not None and isinstance(val, (int, float)) and not math.isnan(val):
            metrics[key] = round(val, 2)

    # Profitability margins (already %)
    for key in ("profitMargins", "operatingMargins", "grossMargins", "returnOnEquity"):
        val = info.get(key)
        if val is not None and isinstance(val, (int, float)) and not math.isnan(val):
            metrics[key] = round(val * 100, 2)

    # Debt / Equity ratio
    metrics["debtToEquity"] = info.get("debtToEquity")

    # Current ratio
    metrics["currentRatio"] = info.get("currentRatio")

    # Revenue growth YoY from income statement (relative, no absolutes)
    try:
        if financials is not None and not financials.empty and "Total Revenue" in financials.index:
            rev = financials.loc["Total Revenue"].dropna()
            if len(rev) >= 2:
                newer = float(rev.iloc[0])
                older = float(rev.iloc[1])
                metrics["revenueGrowthYoY_pct"] = _safe_pct(newer, older)
    except Exception:
        pass

    # D/E from balance sheet when info is missing
    if metrics.get("debtToEquity") is None and balance_sheet is not None and not balance_sheet.empty:
        try:
            idx = balance_sheet.index.tolist()
            debt_key = next((k for k in idx if "Long Term Debt" in str(k)), None)
            eq_key = next((k for k in idx if "Stockholders Equity" in str(k) or "Total Equity" in str(k)), None)
            if debt_key and eq_key:
                debt = float(balance_sheet.loc[debt_key].iloc[0])
                equity = float(balance_sheet.loc[eq_key].iloc[0])
                metrics["debtToEquity"] = _safe_ratio(debt, equity)
        except Exception:
            pass

    return {k: v for k, v in metrics.items() if v is not None}


async def fetch_market_data(ticker: str) -> dict[str, Any]:
    """
    Fetch and return sanitized relative market metrics for a ticker.
    All absolute prices and monetary values are stripped.

    Returns a dict with keys:
      ticker, sector, industry, market_cap_category,
      price_metrics (relative), fundamental_metrics (ratios)
    Raises ValueError if the ticker is invalid / returns no data.
    """
    def _sync_fetch():
        t = yf.Ticker(ticker)
        hist = t.history(period="65d")
        info = t.info or {}
        try:
            balance_sheet = t.balance_sheet
        except Exception:
            balance_sheet = None
        try:
            financials = t.financials
        except Exception:
            financials = None
        return hist, info, balance_sheet, financials

    loop = asyncio.get_event_loop()
    try:
        hist, info, balance_sheet, financials = await loop.run_in_executor(None, _sync_fetch)
    except Exception as exc:
        raise ValueError(f"yfinance error for '{ticker}': {exc}") from exc

    if hist is None or hist.empty:
        raise ValueError(f"No price history found for ticker '{ticker.upper()}'.")

    # Classify market cap (no absolute figure leaked)
    cap = info.get("marketCap")
    if cap:
        if cap >= 10e9:
            cap_cat = "Large Cap (≥$10B)"
        elif cap >= 2e9:
            cap_cat = "Mid Cap ($2B–$10B)"
        elif cap >= 300e6:
            cap_cat = "Small Cap ($300M–$2B)"
        else:
            cap_cat = "Micro Cap (<$300M)"
    else:
        cap_cat = "Unknown"

    return {
        "ticker": ticker.upper(),
        "name": info.get("longName") or info.get("shortName") or ticker.upper(),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "market_cap_category": cap_cat,
        "price_metrics": _compute_price_metrics(hist),
        "fundamental_metrics": _compute_fundamental_metrics(info, balance_sheet, financials),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Prompt assembly — no PII, no absolute amounts
# ─────────────────────────────────────────────────────────────────────────────

def build_prompt_context(
    market_data: dict,
    portfolio_entry: dict | None,
    recent_analyses: list[dict],
    current_price: float | None = None,
) -> str:
    """
    Assemble a fully anonymised context string for the LLM.

    Portfolio cost/target/stop are converted to relative % differences
    vs. the current price before injection – the raw values are never
    forwarded to the model.
    """
    md = market_data
    pm = md.get("price_metrics", {})
    fm = md.get("fundamental_metrics", {})

    def fmt(v, suffix="") -> str:
        return f"{v}{suffix}" if v is not None else "N/A"

    lines = [
        f"TICKER: {md['ticker']}  |  {md['name']}",
        f"SECTOR: {md['sector']}  |  INDUSTRY: {md['industry']}",
        f"MARKET CAP CATEGORY: {md['market_cap_category']}",
        "",
        "── PRICE METRICS (relative, no absolute levels) ──",
        f"  1-day return      : {fmt(pm.get('return_1d_pct'), '%')}",
        f"  5-day return      : {fmt(pm.get('return_5d_pct'), '%')}",
        f"  30-day return     : {fmt(pm.get('return_30d_pct'), '%')}",
        f"  60-day return     : {fmt(pm.get('return_60d_pct'), '%')}",
        f"  30d ann. volatility: {fmt(pm.get('volatility_30d_ann_pct'), '%')}",
        f"  Price vs SMA-20   : {fmt(pm.get('price_vs_sma20_pct'), '%')}",
        f"  Price vs SMA-50   : {fmt(pm.get('price_vs_sma50_pct'), '%')}",
        f"  Volume (5d vs 30d): {fmt(pm.get('volume_ratio_5d_vs_30d'), 'x')}",
        "",
        "── VALUATION MULTIPLES ──",
        f"  Trailing P/E      : {fmt(fm.get('trailingPE'))}",
        f"  Forward P/E       : {fmt(fm.get('forwardPE'))}",
        f"  Price/Book        : {fmt(fm.get('priceToBook'))}",
        f"  EV/EBITDA         : {fmt(fm.get('enterpriseToEbitda'))}",
        "",
        "── FUNDAMENTAL RATIOS ──",
        f"  Gross Margin      : {fmt(fm.get('grossMargins'), '%')}",
        f"  Operating Margin  : {fmt(fm.get('operatingMargins'), '%')}",
        f"  Net Margin        : {fmt(fm.get('profitMargins'), '%')}",
        f"  ROE               : {fmt(fm.get('returnOnEquity'), '%')}",
        f"  Debt/Equity       : {fmt(fm.get('debtToEquity'))}",
        f"  Current Ratio     : {fmt(fm.get('currentRatio'))}",
        f"  Revenue Growth YoY: {fmt(fm.get('revenueGrowthYoY_pct'), '%')}",
        "",
    ]

    # Portfolio context – relative figures only
    if portfolio_entry and current_price:
        cp = current_price
        entry = portfolio_entry.get("entry_cost")
        target = portfolio_entry.get("target_price")
        stop = portfolio_entry.get("stop_loss")
        weight = portfolio_entry.get("relative_weight")

        entry_delta = _safe_pct(cp, entry) if entry else None
        target_delta = _safe_pct(target, cp) if target else None
        stop_delta = _safe_pct(stop, cp) if stop else None

        lines += [
            "── ANONYMISED PORTFOLIO CONTEXT ──",
            f"  Portfolio weight  : {fmt(weight, '%')} of total portfolio",
            f"  Entry vs current  : {fmt(entry_delta, '%')}  (+ = current above entry)",
            f"  Target vs current : {fmt(target_delta, '%')}",
            f"  Stop-loss vs curr : {fmt(stop_delta, '%')}",
            "",
        ]
    else:
        lines += [
            "── PORTFOLIO CONTEXT ──",
            "  No position data on record for this user/ticker.",
            "",
        ]

    # Prior thesis — sanitize before injecting to prevent absolute value leakage.
    # The LLM's own prior outputs may contain absolute prices it inferred or
    # hallucinated; we strip any token that resembles a currency amount.
    if recent_analyses:
        last = recent_analyses[0]
        created = last.get("created_at", "unknown date")
        raw = last.get("ai_response", "")
        sanitized = _strip_absolute_values(raw)[:500]
        lines += [
            "── PRIOR ANALYSIS SUMMARY (sanitized, most recent) ──",
            f"  Date: {created}",
            f"  {sanitized}",
            "",
        ]

    return "\n".join(lines)


import re as _re

# Pass 1 — currency-prefixed/suffixed amounts and bare numbers ≥ 4 digits.
_ABSOLUTE_VALUE_RE = _re.compile(
    r"""
    (?:
        [\$€£¥₹][\s]?\d[\d,\.]*                        # $95, €1,234.56
      | \d[\d,\.]*[\s]?(?:USD|EUR|GBP|JPY|CAD|AUD|CHF) # 1234 USD
      | \b\d{4,}(?:[,\.]\d+)?\b                         # bare ≥4-digit  e.g. 12345
    )
    """,
    _re.VERBOSE | _re.IGNORECASE,
)

# Pass 2 — short absolute prices in financial-context phrases.
# Catches "at 95", "around 250", "target 130.5", "support 80" etc.
# Group 1 = preposition/keyword (kept); Group 2 = number (redacted).
_PRICE_CTX_RE = _re.compile(
    r"\b(at|around|near|below|above|to|target|stop|support|resistance)\s+(\d{2,}(?:\.\d+)?)\b",
    _re.IGNORECASE,
)


def _strip_absolute_values(text: str) -> str:
    """
    Remove tokens from prior AI output that resemble absolute monetary amounts.

    Two-pass strategy:
      1. Currency-symbol/suffix amounts and bare numbers ≥ 4 digits.
      2. Numbers ≥ 2 digits that follow a price-context keyword (e.g. "at 95").
    Percentages (12.5%), P/E ratios, risk scores, and other small ratios are
    preserved because they are not preceded by the listed keywords.
    """
    text = _ABSOLUTE_VALUE_RE.sub("[REDACTED]", text)
    text = _PRICE_CTX_RE.sub(lambda m: f"{m.group(1)} [REDACTED]", text)
    return text


# ─────────────────────────────────────────────────────────────────────────────
# OpenRouter — free-tier LLM
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an elite quantitative investment analyst.
Your task is to produce a structured, multi-point investment analysis based SOLELY
on the anonymised market data and portfolio context provided.

STRICT RULES:
- Never ask for, infer, or mention personal information or identity.
- Never fabricate data not present in the context.
- Base all price targets and stop-losses on PERCENTAGE MOVES from current levels
  (e.g. "+8% target", "-5% stop-loss") since you do not have absolute price data.
- Clearly label each section with the heading shown below.

REQUIRED OUTPUT FORMAT:
1. 📰 NEWS & MACRO IMPACT  — assess sector/market risk visible in the metrics
2. 📈 TECHNICAL ANALYSIS   — interpret moving averages, momentum, volatility
3. 🎯 ENTRY / TARGET / STOP — recommend % entry zone, % target, % stop-loss
4. 🔍 THESIS VALIDATION    — validate or challenge the user's existing position
5. ⚠️  RISK SCORE (1–10)    — justify briefly
6. ✅ CONFIDENCE SCORE (1–10) — justify briefly
7. 📝 SUMMARY              — one concise paragraph

Be direct. Be quantitative. No filler sentences."""


async def chat_completion(prompt_context: str) -> str:
    """
    Send a structured investment analysis request to OpenRouter's free model.
    Returns the assistant's text response.
    Raises httpx.HTTPStatusError on upstream errors.
    """
    settings = get_settings()
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": prompt_context},
    ]

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://ai-investment-assistant",
        "X-Title": "AI Investment Assistant",
    }
    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.3,  # lower = more deterministic / analytical
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except httpx.TimeoutException:
        raise RuntimeError("OpenRouter request timed out (60s).")
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"OpenRouter returned {exc.response.status_code}: {exc.response.text[:300]}"
        ) from exc


# ─────────────────────────────────────────────────────────────────────────────
# Telegram Bot API
# ─────────────────────────────────────────────────────────────────────────────

_TG_MAX_CHARS = 4096  # Telegram hard limit per message


async def send_telegram_message(
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
) -> None:
    """
    Send a text message to a Telegram chat.
    Long messages are automatically split to respect the 4096-character limit.
    """
    settings = get_settings()
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

    # Split into chunks if needed
    chunks = [text[i: i + _TG_MAX_CHARS] for i in range(0, len(text), _TG_MAX_CHARS)]

    async with httpx.AsyncClient(timeout=15) as client:
        for chunk in chunks:
            payload = {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": parse_mode,
            }
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            except httpx.TimeoutException:
                log.error("Telegram send timed out for chat_id=%s", chat_id)
                raise
            except httpx.HTTPStatusError as exc:
                log.error(
                    "Telegram API error %s for chat_id=%s: %s",
                    exc.response.status_code, chat_id, exc.response.text[:200],
                )
                raise


async def register_webhook() -> None:
    """
    (Re-)register this service's webhook URL with Telegram on startup.

    Reads TELEGRAM_WEBHOOK_URL (full public HTTPS URL, e.g.
    https://portfolio-ai-agent-1.onrender.com/webhook/telegram) and
    TELEGRAM_WEBHOOK_SECRET from settings. No-op if TELEGRAM_WEBHOOK_URL is
    not configured, so this is safe to call unconditionally at startup.

    This makes redeploys (Render, etc.) self-healing: every cold start
    re-points Telegram at the current host without any manual setWebhook call.
    """
    settings = get_settings()
    if not settings.TELEGRAM_WEBHOOK_URL:
        log.info("TELEGRAM_WEBHOOK_URL not set — skipping webhook auto-registration.")
        return

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
    payload: dict[str, Any] = {"url": settings.TELEGRAM_WEBHOOK_URL}
    if settings.TELEGRAM_WEBHOOK_SECRET:
        payload["secret_token"] = settings.TELEGRAM_WEBHOOK_SECRET

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, data=payload)
            resp.raise_for_status()
            result = resp.json()
        if result.get("ok"):
            log.info("Telegram webhook registered: %s", settings.TELEGRAM_WEBHOOK_URL)
        else:
            log.error("Telegram webhook registration failed: %s", result)
    except Exception:
        # Never crash startup over this — log and continue serving traffic.
        log.exception("Failed to register Telegram webhook at startup.")
