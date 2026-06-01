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
# AR reminder exclusion list — comma-separated customer emails that should NEVER
# receive automated AR reminders (e.g. large B2B accounts with custom payment terms).
# Jessica manages this list. Empty by default — confirm with Jessica before AR loop goes live.
AR_EXCLUSION_LIST: list[str] = [
    e.strip().lower()
    for e in os.getenv("AR_EXCLUSION_LIST", "").split(",")
    if e.strip()
]
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

# MS Teams — Graph API (Azure AD app, application permissions)
TEAMS_TENANT_ID:     str | None = os.getenv("TEAMS_TENANT_ID")
TEAMS_APP_ID:        str | None = os.getenv("TEAMS_APP_ID")
TEAMS_CLIENT_SECRET: str | None = os.getenv("TEAMS_CLIENT_SECRET")
TEAMS_TEAM_ID:       str | None = os.getenv("TEAMS_TEAM_ID")
TEAMS_CHANNEL_ID:    str | None = os.getenv("TEAMS_CHANNEL_ID")
# Group chat used for invoice approvals: 19:xxxx@thread.v2
# Requires Chat.Read.All + Chat.ReadWrite.All application permissions in Azure AD
TEAMS_CHAT_ID:       str | None = os.getenv("TEAMS_CHAT_ID", "19:b88d010aa8254609937c512aded09e5f@thread.v2")
# Incoming webhook URL (Logic App / Workflows) — for posting TO Teams channel
TEAMS_INCOMING_WEBHOOK_URL: str | None = os.getenv("TEAMS_INCOMING_WEBHOOK_URL")
# Graph API email notifications (Mail.Send application permission)
# FROM must be a valid licensed mailbox in the same Azure AD tenant.
NOTIFICATION_FROM_EMAIL:  str | None = os.getenv("NOTIFICATION_FROM_EMAIL")
NOTIFICATION_TO_EMAILS:   str        = os.getenv("NOTIFICATION_TO_EMAILS", "")  # comma-sep
# Approved senders for Teams APPROVE/REJECT commands (first-name match, case-insensitive)
APPROVED_SENDERS: list[str] = [
    s.strip().lower()
    for s in os.getenv("APPROVED_SENDERS", "robert,ryan,prateek").split(",")
    if s.strip()
]

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
SMTP_FROM:     str        = os.getenv("SMTP_FROM", "nesa@nexgenlogix.com")

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

# Invoice pipeline
MAX_INVOICE_MODIFICATIONS: int = int(os.getenv("MAX_INVOICE_MODIFICATIONS", "5"))

# IMAP — email inbox for nesa@nexgenlogix.com
IMAP_HOST:     str = os.getenv("IMAP_HOST", "outlook.office365.com")
IMAP_PORT:     int = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER:     str | None = os.getenv("IMAP_USER")
IMAP_PASSWORD: str | None = os.getenv("IMAP_PASSWORD")

# Dynamic pricing complexity factors (I-065)
# Set PRICING_COMPLEXITY_ENABLED=true to activate upcharges based on property features.
# Robert must confirm exact weights before enabling in production.
# Features are passed as order properties (pool, shed_count, driveway_count, etc.)
PRICING_COMPLEXITY_ENABLED: bool = os.getenv("PRICING_COMPLEXITY_ENABLED", "false").lower() == "true"

# Upcharge ranges (midpoints used by default; Robert to tune)
COMPLEXITY_FACTORS: dict = {
    "pool":            150,   # swimming pool — midpoint of $100-$200
    "shed":            112,   # per shed — midpoint of $75-$150
    "driveway_extra":  150,   # per extra driveway beyond 1 — midpoint of $100-$200
    "walls_per_10":     75,   # per 10 corners/walls above baseline of 4 — midpoint of $50-$150
    "patio_large":      75,   # large back patio — moderate upcharge
    "remote_rural":    100,   # rural/remote location surcharge (% of base applied separately)
}

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
