import os

from dotenv import load_dotenv

load_dotenv()

# Pipeline behaviour
MAX_REVIEWER_RETRIES: int = 3
MAX_SENDER_RETRIES:   int = int(os.getenv("MAX_SENDER_RETRIES", "3"))
ESTIMATE_DELAY_MIN:   int = 360    # 6 minutes — lower bound of random send delay
ESTIMATE_DELAY_MAX:   int = 780    # 13 minutes — upper bound of random send delay
SEND_HOUR_START:      int = int(os.getenv("SEND_HOUR_START", "8"))   # 8 AM ET
SEND_HOUR_END:        int = int(os.getenv("SEND_HOUR_END", "18"))    # 6 PM ET
AR_ESCALATION_DAYS:        int = 90
AR_ALERT_DAYS_60:          int = 60
APPROVAL_TIMEOUT_HOURS:    int = int(os.getenv("APPROVAL_TIMEOUT_HOURS", "24"))
ELEVATION_CERT_PRICE: int = 225
SERVICE_STATE:        str = "FL"

# FTF API
FTF_API_BASE_URL: str = os.getenv("FTF_API_BASE_URL", "https://stage.fieldtofinish.jobs/ftf-ai-api/v1")
FTF_API_KEY:      str | None = os.getenv("FTF_API_KEY")
FTF_ORDER_URL:    str = os.getenv("FTF_ORDER_URL", "https://stage.fieldtofinish.jobs/admin/orders")

# FTF Books (AR Excel download — session-cookie auth)
FTF_BOOKS_BASE_URL: str      = os.getenv("FTF_BOOKS_BASE_URL", "https://stage.fieldtofinish.jobs")
FTF_BOOKS_USER:     str | None = os.getenv("FTF_BOOKS_USER")
FTF_BOOKS_PASSWORD: str | None = os.getenv("FTF_BOOKS_PASSWORD")

# Anthropic
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")

# PostgreSQL
DB_HOST:     str       = os.getenv("DB_HOST", "localhost")
DB_PORT:     int       = int(os.getenv("DB_PORT", "5432"))
DB_NAME:     str       = os.getenv("DB_NAME", "ftf_agentic_ai")
DB_USER:     str | None = os.getenv("DB_USER")
DB_PASSWORD: str | None = os.getenv("DB_PASSWORD")

# MS Teams — Graph API (Azure AD app, no webhook URLs needed)
TEAMS_TENANT_ID:     str | None = os.getenv("TEAMS_TENANT_ID")
TEAMS_APP_ID:        str | None = os.getenv("TEAMS_APP_ID")
TEAMS_CLIENT_SECRET: str | None = os.getenv("TEAMS_CLIENT_SECRET")
TEAMS_TEAM_ID:       str | None = os.getenv("TEAMS_TEAM_ID")
TEAMS_CHANNEL_ID:    str | None = os.getenv("TEAMS_CHANNEL_ID")

# MS Teams — legacy webhook vars (kept for backward compat; unused once Graph API is live)
TEAMS_WEBHOOK_URL:             str | None = os.getenv("TEAMS_WEBHOOK_URL")
TEAMS_APPROVAL_WEBHOOK_URL:    str | None = os.getenv("TEAMS_APPROVAL_WEBHOOK_URL")
TEAMS_OUTGOING_WEBHOOK_SECRET: str | None = os.getenv("TEAMS_OUTGOING_WEBHOOK_SECRET")
APPROVAL_RECEIVER_HOST:        str        = os.getenv("APPROVAL_RECEIVER_HOST", "0.0.0.0")
APPROVAL_RECEIVER_PORT:        int        = int(os.getenv("APPROVAL_RECEIVER_PORT", "5001"))

# SMTP — monthly statement email delivery
SMTP_HOST:     str | None = os.getenv("SMTP_HOST")
SMTP_PORT:     int        = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER:     str | None = os.getenv("SMTP_USER")
SMTP_PASSWORD: str | None = os.getenv("SMTP_PASSWORD")
SMTP_FROM:     str        = os.getenv("SMTP_FROM", "statements@nexgensurveying.com")

# Monthly statements — file output
STATEMENT_OUTPUT_DIR: str = os.getenv(
    "STATEMENT_OUTPUT_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "statements"),
)

# OpenAI
OPENAI_API_KEY:     str | None = os.getenv("OpenAI_API_KEY")
OPENAI_CHAT_MODEL:  str        = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_TTS_MODEL:   str        = os.getenv("OPENAI_TTS_MODEL", "tts-1-hd")
OPENAI_TTS_VOICE:   str        = os.getenv("OPENAI_TTS_VOICE", "nova")        # warm female
OPENAI_EMBED_MODEL: str        = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

# Hermes (local via Ollama)
HERMES_MODEL:    str = os.getenv("HERMES_MODEL", "hermes3")
HERMES_BASE_URL: str = os.getenv("HERMES_BASE_URL", "http://localhost:11434")

# Obsidian (Local REST API plugin — port 27123 is default)
OBSIDIAN_API_KEY:  str | None = os.getenv("Obsidian")
OBSIDIAN_BASE_URL: str        = os.getenv("OBSIDIAN_BASE_URL", "http://localhost:27123")

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# FTF API status keyword map (confirmed 2026-05-27 — Prateek)
# Keys = FTF API query param values; values = CRM display labels.
# "needs_fp" and "set_up" are special-cased: not the CRM label, must use these exact keys.
# "set_up" (Set Up) has 0 orders in production — kept for completeness.
FTF_STATUS_KEYWORD_MAP: dict[str, str] = {
    "pending":        "Pending",
    "quote":          "Quote",
    "assigned":       "Assigned",
    "in_field":       "In-Field",
    "drafting_queue": "Drafting Queue",
    "drafting":       "Drafting",
    "checking":       "Checking",
    "complete":       "Complete",
    "delivered":      "Delivered",
    "on_hold":        "On Hold",
    "in_progress":    "In Progress",
    "go_back":        "Go Back",
    "set_corners":    "Set Corners",
    "re_draft":       "Re-Draft",
    "canceled":       "Canceled",
    "needs_fp":       "Needs FP",   # special key — CRM label differs
    "set_up":         "Set Up",     # special key — 0 orders in prod; retained for completeness
}
