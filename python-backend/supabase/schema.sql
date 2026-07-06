-- ============================================================
-- AI Investment Assistant — Supabase schema
-- Run once in the Supabase SQL editor for your project.
-- ============================================================

-- ── portfolio_memory ─────────────────────────────────────────────────────────
-- Stores per-user, per-ticker position metadata.
-- Absolute monetary values (entry_cost, target_price, stop_loss) are stored
-- here for user reference but are NEVER forwarded to the LLM verbatim —
-- routes.py converts them to relative % differences before prompt injection.

CREATE TABLE IF NOT EXISTS portfolio_memory (
    id               UUID          DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id          TEXT          NOT NULL,           -- Telegram user_id (string)
    ticker           TEXT          NOT NULL,           -- e.g. 'AAPL'
    relative_weight  NUMERIC(6,4)  NOT NULL DEFAULT 0, -- % of portfolio (0–100)
    entry_cost       NUMERIC(12,4) NOT NULL DEFAULT 0, -- average cost basis
    target_price     NUMERIC(12,4) NOT NULL DEFAULT 0,
    stop_loss        NUMERIC(12,4) NOT NULL DEFAULT 0,
    updated_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, ticker)
);

-- Keep updated_at current automatically
CREATE OR REPLACE FUNCTION portfolio_memory_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_portfolio_memory_updated_at ON portfolio_memory;
CREATE TRIGGER trg_portfolio_memory_updated_at
    BEFORE UPDATE ON portfolio_memory
    FOR EACH ROW EXECUTE FUNCTION portfolio_memory_set_updated_at();


-- ── analysis_logs ────────────────────────────────────────────────────────────
-- Immutable audit trail: every AI analysis run is persisted here.
-- prompt_context stores the sanitized data fed to the model.
-- ai_response stores the raw model output for review / retraining.

CREATE TABLE IF NOT EXISTS analysis_logs (
    id             UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id        TEXT        NOT NULL,
    ticker         TEXT        NOT NULL,
    prompt_context TEXT        NOT NULL,
    ai_response    TEXT        NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast per-user, per-ticker history queries
CREATE INDEX IF NOT EXISTS idx_analysis_logs_user_ticker_created
    ON analysis_logs (user_id, ticker, created_at DESC);
