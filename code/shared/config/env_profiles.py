"""
FTF Invoice Pipeline — deployment environment profiles.

HOW TO SWITCH ENVIRONMENTS
──────────────────────────
  Local dev / one-off  : Change ACTIVE_ENV below (committed to git — safe to edit)
  GitHub Actions       : Set DEPLOY_ENV secret to "stage" or "prod"
                         The secret always overrides ACTIVE_ENV.

  stage → data from stage.fieldtofinish.jobs  (default — safe for all testing)
  prod  → data from fieldtofinish.jobs        (live customer data — see checklist)

SECURITY NOTE
──────────────
  This file is committed to git. Credentials stored here are visible to anyone
  with repo access. For production, prefer moving sensitive values (passwords,
  API keys) to GitHub Secrets — they override profile defaults automatically.
  Treat this file as "config for the team", not a secrets vault.

PROD DEPLOYMENT CHECKLIST
──────────────────────────
  [ ] Set DEPLOY_ENV secret to "prod" in GitHub → Settings → Secrets
  [ ] Delete EMAIL_OVERRIDE_ALL GitHub Secret — prod must never redirect emails
  [ ] Confirm FTF_API_KEY is the production key (not stage)
  [ ] Confirm MYSQL_HOST / MYSQL_DB point to production RDS
  [ ] Prateek sign-off received

LEARNED PRICING RULES — STAGE → PROD
──────────────────────────────────────
  data/learned_rules.json and data/pricing_rules.json are committed to git.
  All pricing intelligence learned during stage testing carries over to prod
  automatically when the repo is deployed — no manual copy needed.
"""

import os

# ── Change this one line to switch environments (local dev) ───────────────────
ACTIVE_ENV: str = "stage"   # "stage" | "prod"
# ─────────────────────────────────────────────────────────────────────────────

_STAGE = "https://stage.fieldtofinish.jobs"
_PROD  = "https://fieldtofinish.jobs"

PROFILES: dict[str, dict[str, str]] = {
    "stage": {
        # ── FTF URLs ──────────────────────────────────────────────────────────
        "FTF_API_BASE_URL":    f"{_STAGE}/ftf-ai-api/v1",
        "FTF_ORDER_URL":       f"{_STAGE}/order",
        "FTF_SITE_BASE_URL":   _STAGE,
        "FTF_PORTAL_BASE_URL": _STAGE,
        "FTF_BOOKS_BASE_URL":  _STAGE,
        # ── FTF Portal credentials ────────────────────────────────────────────
        "FTF_PORTAL_USER":     "nesa",
        "FTF_PORTAL_PASS":     "",        # set via GitHub Secret FTF_PORTAL_PASS
        # ── FTF Books credentials ─────────────────────────────────────────────
        "FTF_BOOKS_USER":      "nesa",
        "FTF_BOOKS_PASSWORD":  "",        # set via GitHub Secret FTF_BOOKS_PASSWORD
        # ── Pipeline behaviour ────────────────────────────────────────────────
        "LOG_LEVEL":           "DEBUG",
        "INVOICE_BATCH_SIZE":  "5",
        "EMAIL_OVERRIDE_ALL":  "",        # set via GitHub Secret for stage testing
    },
    "prod": {
        # ── FTF URLs ──────────────────────────────────────────────────────────
        "FTF_API_BASE_URL":    f"{_PROD}/ftf-ai-api/v1",
        "FTF_ORDER_URL":       f"{_PROD}/order",
        "FTF_SITE_BASE_URL":   _PROD,
        "FTF_PORTAL_BASE_URL": _PROD,
        "FTF_BOOKS_BASE_URL":  _PROD,
        # ── FTF Portal credentials ────────────────────────────────────────────
        "FTF_PORTAL_USER":     "nesa",
        "FTF_PORTAL_PASS":     "",        # set via GitHub Secret FTF_PORTAL_PASS
        # ── FTF Books credentials ─────────────────────────────────────────────
        "FTF_BOOKS_USER":      "nesa",
        "FTF_BOOKS_PASSWORD":  "",        # set via GitHub Secret FTF_BOOKS_PASSWORD
        # ── Pipeline behaviour ────────────────────────────────────────────────
        "LOG_LEVEL":           "INFO",
        "INVOICE_BATCH_SIZE":  "10",
        "EMAIL_OVERRIDE_ALL":  "",        # MUST stay empty — never redirect in prod
    },
}


def active_profile() -> dict[str, str]:
    """Return the active environment profile dict.

    Priority: DEPLOY_ENV env var > ACTIVE_ENV constant in this file.
    Raises ValueError for unknown environment names.
    """
    env = (os.getenv("DEPLOY_ENV") or ACTIVE_ENV).strip().lower()
    if env not in PROFILES:
        raise ValueError(
            f"Unknown DEPLOY_ENV='{env}' — valid values: {list(PROFILES)}"
        )
    return PROFILES[env]


def active_env_name() -> str:
    """Return the resolved environment name ('stage' or 'prod')."""
    return (os.getenv("DEPLOY_ENV") or ACTIVE_ENV).strip().lower()
