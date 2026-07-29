# Model IDs verified 2026-07-29
CLAUDE_HAIKU  = "claude-haiku-4-5-20251001"
CLAUDE_SONNET = "claude-sonnet-4-6"          # retained for reference / rollback
CLAUDE_OPUS   = "claude-opus-4-8"            # latest Opus

# Haiku — simple/fast agents (no reasoning required)
MONITOR_MODEL   = CLAUDE_HAIKU
AR_SCANNER_MODEL = CLAUDE_HAIKU
SCHEDULER_MODEL = CLAUDE_HAIKU

# Opus — leadership/manager roles (complex tasks)
PRATEEK_MODEL     = CLAUDE_OPUS
DEV_MANAGER_MODEL = CLAUDE_OPUS
QA_MANAGER_MODEL  = CLAUDE_OPUS

# Opus — all reasoning agents (switched from Sonnet -> Opus on 2026-07-29 per Prateek).
# To roll back to Sonnet, repoint these to CLAUDE_SONNET.
ORCHESTRATOR_MODEL      = CLAUDE_OPUS
CLASSIFIER_MODEL        = CLAUDE_OPUS
HUMAN_GATE_MODEL        = CLAUDE_OPUS
PRICING_MODEL           = CLAUDE_OPUS
WRITER_MODEL            = CLAUDE_OPUS
REVIEWER_MODEL          = CLAUDE_OPUS
REWRITER_MODEL          = CLAUDE_OPUS
SENDER_MODEL            = CLAUDE_OPUS
REPORTER_MODEL          = CLAUDE_OPUS
AR_WRITER_MODEL         = CLAUDE_OPUS
AR_REMINDER_MODEL       = CLAUDE_OPUS
AR_ESCALATION_MODEL     = CLAUDE_OPUS
STATEMENT_COMPILER_MODEL = CLAUDE_OPUS
STATEMENT_FORMATTER_MODEL = CLAUDE_OPUS
STATEMENT_SENDER_MODEL  = CLAUDE_OPUS

# Vision — aerial image + property photo analysis (Opus supports multimodal)
VISION_MODEL = CLAUDE_OPUS
