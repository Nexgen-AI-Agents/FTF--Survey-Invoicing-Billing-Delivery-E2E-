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
