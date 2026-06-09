import os

from dotenv import load_dotenv

load_dotenv()

from config.env_profiles import active_profile, active_env_name  # noqa: E402

_PROFILE = active_profile()
DEPLOY_ENV: str = active_env_name()   # "stage" | "prod" — readable by any agent

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

# Internal NexGen emails that should never enter the invoice pipeline.
# Orders with these as customer_email are internal quote/routing addresses,
# not real client emails — they have no billable invoice target.
INTERNAL_SKIP_EMAILS: set[str] = {
    "quotes@nexgensurveying.com",
}
APPROVAL_TIMEOUT_HOURS:    int = int(os.getenv("APPROVAL_TIMEOUT_HOURS", "24"))
# ── Pricing reference constants (fed to Claude as context — not applied by code) ──
# Survey base rate fallbacks — used ONLY when ng_company.ng_rate is 0 / unset.
# Primary rate always comes from ng_company.ng_rate (negotiated per client).
PRICE_SURVEY_FALLBACK_INDIVIDUAL: float = 475.0   # one-off + new title company
PRICE_SURVEY_FALLBACK_OLD_TITLE:  float = 400.0   # established title company

# EC is always $275 for all client types (Robert/Ryan adjust exceptions manually)
PRICE_EC_BASE: float = 275.0

# Complexity upcharge reference ranges — midpoints validated by land surveyor consultation.
# These are GUIDELINES for Claude's reasoning, not hard rule amounts.
COMPLEXITY_REFERENCE: dict = {
    "monroe_county":    150.0,   # remote Keys mobilisation
    "pool":              62.0,   # pool / screened enclosure locate
    "waterfront_canal":  87.0,   # riparian / OHWL determination
    "metes_and_bounds": 100.0,   # no plat; deed-call boundary
    "heavy_vegetation": 112.0,   # line-of-sight cutting
    "zone_ve_ec":        50.0,   # coastal VE zone EC complexity (EC component only)
    "lot_0.31_0.50_ac":  62.0,
    "lot_0.51_1.00_ac": 137.0,
    "lot_1.01_2.00_ac": 275.0,
    "lot_2.01_5.00_ac": 550.0,
    # lot > 5.00 ac → ESCALATE; do not auto-price
}

# Topo reference pricing by lot size — baseline for Claude's reasoning
TOPO_REFERENCE: dict = {
    "lot_0.00_0.30_ac":  700.0,
    "lot_0.31_0.50_ac":  825.0,
    "lot_0.51_1.00_ac": 1100.0,
    # > 1.00 ac → ESCALATE
}

# New title company thresholds (registered on/after Jan 1 of NEW_TITLE_YEAR_CUTOFF
# AND fewer than NEW_TITLE_ORDER_CUTOFF total orders)
NEW_TITLE_YEAR_CUTOFF:  int = 2025
NEW_TITLE_ORDER_CUTOFF: int = 20

# Legacy — kept for backward compatibility; superseded by PRICE_EC_BASE above
ELEVATION_CERT_PRICE: int = 275
COMPLEXITY_FACTORS = COMPLEXITY_REFERENCE  # Sprint 9 alias — renamed to COMPLEXITY_REFERENCE in Sprint 11
SERVICE_STATE:        str = "FL"

# FTF API
FTF_API_BASE_URL: str = os.getenv("FTF_API_BASE_URL") or _PROFILE["FTF_API_BASE_URL"]
FTF_API_KEY:      str | None = os.getenv("FTF_API_KEY")
FTF_ORDER_URL:    str = os.getenv("FTF_ORDER_URL") or _PROFILE["FTF_ORDER_URL"]
# OneDrive approval spreadsheet (Graph API — Files.ReadWrite.All application permission)
ONEDRIVE_FILE_USER:  str = os.getenv("ONEDRIVE_FILE_USER",  "nesa@nexgenlogix.com")
ONEDRIVE_FILE_PATH:  str = os.getenv("ONEDRIVE_FILE_PATH",  "Documents/FTF-Invoicing Agent.xlsx")
ONEDRIVE_SHARE_URL:  str = os.getenv("ONEDRIVE_SHARE_URL",  "")   # sharing link — preferred over path lookup
ONEDRIVE_SHEET_NAME: str = os.getenv("ONEDRIVE_SHEET_NAME", "Approvals")
ONEDRIVE_TABLE_NAME: str = os.getenv("ONEDRIVE_TABLE_NAME", "ApprovalTable")

# Pay Now link generation — uses same Fernet key as the FTF portal (data_vars['hash_key'])
FTF_PAY_HASH_KEY:  str = os.getenv("FTF_PAY_HASH_KEY", "")
FTF_SITE_BASE_URL: str = os.getenv("FTF_SITE_BASE_URL") or _PROFILE["FTF_SITE_BASE_URL"]

# FTF Portal — nesa HR user auth (invoice generation + delivery)
FTF_PORTAL_BASE_URL: str = os.getenv("FTF_PORTAL_BASE_URL") or _PROFILE["FTF_PORTAL_BASE_URL"]
FTF_PORTAL_USER:     str = os.getenv("FTF_PORTAL_USER") or _PROFILE["FTF_PORTAL_USER"]
FTF_PORTAL_PASS:     str = os.getenv("FTF_PORTAL_PASS") or _PROFILE["FTF_PORTAL_PASS"]

# FTF Books (AR Excel download — session-cookie auth)
FTF_BOOKS_BASE_URL: str      = os.getenv("FTF_BOOKS_BASE_URL") or _PROFILE["FTF_BOOKS_BASE_URL"]
FTF_BOOKS_USER:     str      = os.getenv("FTF_BOOKS_USER") or _PROFILE["FTF_BOOKS_USER"]
FTF_BOOKS_PASSWORD: str      = os.getenv("FTF_BOOKS_PASSWORD") or _PROFILE["FTF_BOOKS_PASSWORD"]

# Anthropic
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")

# MySQL — FTF stage DB (direct connection for Sprint 11 invoice pipeline)
MYSQL_HOST:     str = os.getenv("MYSQL_HOST") or os.getenv("FTF_PROD_MYSQL_HOST", "")
MYSQL_PORT:     int = int(os.getenv("MYSQL_PORT") or os.getenv("FTF_PROD_MYSQL_PORT") or "3306")
MYSQL_USER:     str = os.getenv("MYSQL_USER") or os.getenv("FTF_PROD_MYSQL_USER", "")
MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD") or os.getenv("FTF_PROD_MYSQL_PASS") or os.getenv("FTF_PROD_MYSQL_PASSWORD", "")
MYSQL_DB:       str = os.getenv("MYSQL_DB") or os.getenv("FTF_PROD_MYSQL_DB", "")

# Azure AD App (Graph API — Files.ReadWrite.All, Mail.Send)
# App: FTF Estimate Bot | Registered 2026-05-28 | Secret valid 24 months
AZURE_TENANT_ID:     str | None = os.getenv("AZURE_TENANT_ID")
AZURE_APP_ID:        str | None = os.getenv("AZURE_APP_ID")
AZURE_CLIENT_SECRET: str | None = os.getenv("AZURE_CLIENT_SECRET")
# Graph API email notifications (Mail.Send application permission)
# FROM must be a valid licensed mailbox in the same Azure AD tenant.
NOTIFICATION_FROM_EMAIL:  str | None = os.getenv("NOTIFICATION_FROM_EMAIL")
NOTIFICATION_TO_EMAILS:   str        = os.getenv("NOTIFICATION_TO_EMAILS", "")  # comma-sep
# Approved senders for invoice APPROVE/REJECT/HOLD actions.
# Format: "name:email,name:email" — email verification enforced when present.
_APPROVED_RAW = os.getenv("APPROVED_SENDERS", "robert,ryan,prateek")
APPROVED_SENDERS: list[str] = []        # first names (lowercase)
APPROVED_SENDER_EMAILS: set[str] = set()  # emails (lowercase) — empty = name-only check
APPROVED_SENDER_EMAIL_MAP: dict[str, str] = {}  # first_name → email

for _entry in _APPROVED_RAW.split(","):
    _entry = _entry.strip()
    if not _entry:
        continue
    if ":" in _entry:
        _name, _email = _entry.split(":", 1)
        _n = _name.strip().lower()
        _e = _email.strip().lower()
        APPROVED_SENDERS.append(_n)
        APPROVED_SENDER_EMAILS.add(_e)
        APPROVED_SENDER_EMAIL_MAP[_n] = _e
    else:
        APPROVED_SENDERS.append(_entry.lower())

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
OPENAI_API_KEY:     str | None = os.getenv("OPENAI_API_KEY") or os.getenv("OpenAI_API_KEY")
OPENAI_CHAT_MODEL:  str        = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_TTS_MODEL:   str        = os.getenv("OPENAI_TTS_MODEL", "tts-1-hd")
OPENAI_TTS_VOICE:   str        = os.getenv("OPENAI_TTS_VOICE", "nova")        # warm female
OPENAI_EMBED_MODEL: str        = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

LOG_LEVEL: str = os.getenv("LOG_LEVEL") or _PROFILE["LOG_LEVEL"]

# Invoice pipeline
MAX_INVOICE_MODIFICATIONS: int = int(os.getenv("MAX_INVOICE_MODIFICATIONS", "5"))
INVOICE_BATCH_SIZE:        int = int(os.getenv("INVOICE_BATCH_SIZE") or _PROFILE["INVOICE_BATCH_SIZE"])
# Testing override — when set, ALL invoice emails are redirected to this address.
# MUST be empty (or secret deleted) in prod. Guarded below.
EMAIL_OVERRIDE_ALL: str = os.getenv("EMAIL_OVERRIDE_ALL", "")

if DEPLOY_ENV == "prod" and EMAIL_OVERRIDE_ALL:
    raise RuntimeError(
        "EMAIL_OVERRIDE_ALL is set but DEPLOY_ENV=prod — "
        "delete or clear the EMAIL_OVERRIDE_ALL GitHub Secret before running in production."
    )

# IMAP — email inbox for nesa@nexgenlogix.com
IMAP_HOST:     str = os.getenv("IMAP_HOST", "outlook.office365.com")
IMAP_PORT:     int = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER:     str | None = os.getenv("IMAP_USER")
IMAP_PASSWORD: str | None = os.getenv("IMAP_PASSWORD")

# Google Maps — aerial/satellite image fetch for property analysis
GOOGLE_MAPS_API_KEY: str | None = os.getenv("GOOGLE_MAPS_API_KEY")

# Legacy complexity flag — no longer used; pricing now handled by AI reasoning in A3
PRICING_COMPLEXITY_ENABLED: bool = False

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
