import os

from dotenv import load_dotenv

load_dotenv()

# Pipeline behaviour
MAX_REVIEWER_RETRIES: int = 3
ESTIMATE_DELAY_MIN:   int = 360    # 6 minutes — lower bound of random send delay
ESTIMATE_DELAY_MAX:   int = 780    # 13 minutes — upper bound of random send delay
AR_ESCALATION_DAYS:        int = 90
APPROVAL_TIMEOUT_HOURS:    int = int(os.getenv("APPROVAL_TIMEOUT_HOURS", "24"))
ELEVATION_CERT_PRICE: int = 225
SERVICE_STATE:        str = "FL"

# FTF API
FTF_API_BASE_URL: str = os.getenv("FTF_API_BASE_URL", "https://stage.fieldtofinish.jobs/ftf-ai-api/v1")
FTF_API_KEY:      str | None = os.getenv("FTF_API_KEY")

# Anthropic
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")

# PostgreSQL
DB_HOST:     str       = os.getenv("DB_HOST", "localhost")
DB_PORT:     int       = int(os.getenv("DB_PORT", "5432"))
DB_NAME:     str       = os.getenv("DB_NAME", "ftf_agentic_ai")
DB_USER:     str | None = os.getenv("DB_USER")
DB_PASSWORD: str | None = os.getenv("DB_PASSWORD")

# MS Teams
TEAMS_WEBHOOK_URL: str | None = os.getenv("TEAMS_WEBHOOK_URL")

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
