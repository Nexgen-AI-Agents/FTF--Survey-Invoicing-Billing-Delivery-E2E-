-- FTF Agentic AI OS — PostgreSQL Schema
-- Run: psql -U $DB_USER -d $DB_NAME -f db/schema.sql

-- ─────────────────────────────────────────
-- 1. processed_orders
--    Tracks every FTF order through the estimate pipeline.
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS processed_orders (
    id                  SERIAL PRIMARY KEY,
    order_id            VARCHAR(50)     UNIQUE NOT NULL,
    status              VARCHAR(50)     NOT NULL DEFAULT 'pending',
    -- status values: pending | classified | priced | written | reviewed | sent | flagged | awaiting_approval | approved | rejected | error
    -- draft_estimate: AI-generated estimate email text (set by Agent 6, validated by Agent 7)

    service_type        VARCHAR(100),
    customer_email      VARCHAR(255),
    property_lat        NUMERIC(10, 6),
    property_lng        NUMERIC(10, 6),
    is_flood_zone       BOOLEAN,
    estimate_amount     NUMERIC(10, 2),
    flag_reason         TEXT,
    retry_count         INTEGER         NOT NULL DEFAULT 0,

    draft_estimate      TEXT,

    classified_at       TIMESTAMP,
    priced_at           TIMESTAMP,
    written_at          TIMESTAMP,
    reviewed_at         TIMESTAMP,
    sent_at             TIMESTAMP,
    flagged_at          TIMESTAMP,

    created_at          TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_po_order_id ON processed_orders (order_id);
CREATE INDEX IF NOT EXISTS idx_po_status   ON processed_orders (status);


-- ─────────────────────────────────────────
-- 2. ar_reminders
--    Tracks AR follow-up state per unpaid invoice.
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ar_reminders (
    id                      SERIAL PRIMARY KEY,
    order_id                VARCHAR(50)     NOT NULL,
    customer_email          VARCHAR(255),
    invoice_amount          NUMERIC(10, 2),
    invoice_date            DATE,
    days_overdue            INTEGER,
    reminder_level          INTEGER         NOT NULL DEFAULT 1,
    -- reminder_level values: 1=first | 2=second | 3=escalate

    last_reminder_sent_at   TIMESTAMP,
    next_reminder_date      DATE,
    status                  VARCHAR(50)     NOT NULL DEFAULT 'pending',
    -- status values: pending | sent | escalated | paid | excluded

    created_at              TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ar_order_id   ON ar_reminders (order_id);
CREATE INDEX IF NOT EXISTS idx_ar_status     ON ar_reminders (status);
CREATE INDEX IF NOT EXISTS idx_ar_next_date  ON ar_reminders (next_reminder_date);


-- ─────────────────────────────────────────
-- 3. monthly_statements
--    Tracks B2B statement generation and delivery per client per month.
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS monthly_statements (
    id              SERIAL PRIMARY KEY,
    client_email    VARCHAR(255)    NOT NULL,
    statement_month DATE            NOT NULL,
    -- statement_month is always the first day of the month (e.g. 2026-06-01)

    order_count     INTEGER         NOT NULL DEFAULT 0,
    total_amount    NUMERIC(10, 2),
    excel_path      TEXT,
    pdf_path        TEXT,
    sent_at         TIMESTAMP,
    status          VARCHAR(50)     NOT NULL DEFAULT 'pending',
    -- status values: pending | generated | sent | failed

    created_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ms_client ON monthly_statements (client_email);
CREATE INDEX IF NOT EXISTS idx_ms_month  ON monthly_statements (statement_month);


-- ─────────────────────────────────────────
-- 4. agent_decision_log
--    Immutable audit trail of every agent decision.
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_decision_log (
    id              SERIAL PRIMARY KEY,
    agent_name      VARCHAR(100)    NOT NULL,
    order_id        VARCHAR(50),
    decision        VARCHAR(100)    NOT NULL,
    reason          TEXT,
    input_summary   TEXT,
    output_summary  TEXT,
    model_used      VARCHAR(100),
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_adl_order_id  ON agent_decision_log (order_id);
CREATE INDEX IF NOT EXISTS idx_adl_agent     ON agent_decision_log (agent_name);
CREATE INDEX IF NOT EXISTS idx_adl_created   ON agent_decision_log (created_at);


-- ─────────────────────────────────────────
-- 5. excluded_ar_clients
--    Clients permanently excluded from AR reminders (Jessica-managed).
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS excluded_ar_clients (
    id              SERIAL PRIMARY KEY,
    client_email    VARCHAR(255)    UNIQUE NOT NULL,
    reason          TEXT,
    excluded_by     VARCHAR(100),
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exc_email ON excluded_ar_clients (client_email);


-- ─────────────────────────────────────────
-- 6. loop_state
--    Tracks the run state of each automated loop (estimate, ar, statement, memory).
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS loop_state (
    id           SERIAL PRIMARY KEY,
    loop_name    VARCHAR(100)  UNIQUE NOT NULL,
    -- loop_name values: estimate_generation | ar_followup | monthly_statements | memory
    status       VARCHAR(50)   NOT NULL DEFAULT 'idle',
    -- status values: idle | running | completed | error
    last_run_at  TIMESTAMP,
    next_run_at  TIMESTAMP,
    error_count  INTEGER       NOT NULL DEFAULT 0,
    last_error   TEXT,
    updated_at   TIMESTAMP     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ls_loop_name ON loop_state (loop_name);


-- ─────────────────────────────────────────
-- 7. LISTEN/NOTIFY trigger
--    Fires pg_notify('order_state_changed', 'order_id:status') on every
--    INSERT or status UPDATE to processed_orders.
--    Consumed by agent_00_listener.py (real-time pipeline trigger).
-- ─────────────────────────────────────────
CREATE OR REPLACE FUNCTION notify_order_state_change()
RETURNS trigger AS $$
BEGIN
    PERFORM pg_notify('order_state_changed', NEW.order_id || ':' || NEW.status);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_processed_orders_notify ON processed_orders;
CREATE TRIGGER trg_processed_orders_notify
    AFTER INSERT OR UPDATE OF status ON processed_orders
    FOR EACH ROW
    EXECUTE FUNCTION notify_order_state_change();
