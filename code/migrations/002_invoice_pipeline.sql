-- Migration 002: Invoice Pipeline (Sprint 11)
-- Run: psql -d ftf_agentic_ai -f 002_invoice_pipeline.sql

-- New columns on processed_orders for the invoice pipeline
ALTER TABLE processed_orders
    ADD COLUMN IF NOT EXISTS invoice_draft         TEXT,
    ADD COLUMN IF NOT EXISTS data_sources          TEXT,
    ADD COLUMN IF NOT EXISTS approval_message_id   TEXT,
    ADD COLUMN IF NOT EXISTS modification_count    INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS invoice_id            TEXT,
    ADD COLUMN IF NOT EXISTS client_name           TEXT,
    ADD COLUMN IF NOT EXISTS property_address      TEXT,
    ADD COLUMN IF NOT EXISTS data_collected_at     TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS draft_posted_at       TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS invoice_created_at    TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS processed_reply_ids   TEXT DEFAULT '[]';

-- Human corrections / learnings table
CREATE TABLE IF NOT EXISTS invoice_learnings (
    id               SERIAL PRIMARY KEY,
    order_id         TEXT,
    original_draft   TEXT,
    human_correction TEXT,
    learned_rule     TEXT,
    service_type     TEXT,
    county           TEXT,
    entered_by       TEXT DEFAULT 'system',
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invoice_learnings_service
    ON invoice_learnings (service_type);
CREATE INDEX IF NOT EXISTS idx_invoice_learnings_county
    ON invoice_learnings (county);

-- Index for fast status lookups on the new pipeline statuses
CREATE INDEX IF NOT EXISTS idx_processed_orders_status_invoice
    ON processed_orders (status)
    WHERE status IN (
        'invoice_needed',
        'data_collected',
        'invoice_draft_posted',
        'invoice_modification_requested',
        'invoice_approved',
        'invoice_rejected',
        'invoice_finalized',
        'invoice_sent',
        'invoice_needs_human'
    );
