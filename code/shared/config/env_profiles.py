"""
FTF Invoice Pipeline — deployment environment profiles.

HOW TO SWITCH ENVIRONMENTS
──────────────────────────
  Local dev / one-off  : Change ACTIVE_ENV below (committed to git — safe to edit)
  GitHub Actions       : Set DEPLOY_ENV secret to "stage" or "prod"
                         The secret always overrides ACTIVE_ENV.

  stage → data from stage.fieldtofinish.jobs  (default — safe for all testing)
  prod  → data from app.fieldtofinish.jobs    (live customer data — see checklist)

PROD DEPLOYMENT CHECKLIST
──────────────────────────
  [ ] Set DEPLOY_ENV secret to "prod" in GitHub → Settings → Secrets
  [ ] Clear (or delete) FTF_API_BASE_URL, FTF_ORDER_URL, FTF_SITE_BASE_URL,
      FTF_PORTAL_BASE_URL, FTF_BOOKS_BASE_URL GitHub Secrets — profile handles them
  [ ] Delete EMAIL_OVERRIDE_ALL GitHub Secret — prod never redirects customer emails
  [ ] FTF_API_KEY is the production key (not stage)
  [ ] MYSQL_HOST / MYSQL_DB point to production RDS
  [ ] Prateek sign-off received
"""

import os

# ── Change this one line to switch environments (local dev) ───────────────────
ACTIVE_ENV: str = "stage"   # "stage" | "prod"
# ─────────────────────────────────────────────────────────────────────────────

_STAGE = "https://stage.fieldtofinish.jobs"
_PROD  = "https://fieldtofinish.jobs"

PROFILES: dict[str, dict[str, str]] = {
    "stage": {
        "FTF_API_BASE_URL":    f"{_STAGE}/ftf-ai-api/v1",
        "FTF_ORDER_URL":       f"{_STAGE}/order",
        "FTF_SITE_BASE_URL":   _STAGE,
        "FTF_PORTAL_BASE_URL": _STAGE,
        "FTF_BOOKS_BASE_URL":  _STAGE,
        "LOG_LEVEL":           "DEBUG",
        "INVOICE_BATCH_SIZE":  "5",
    },
    "prod": {
        "FTF_API_BASE_URL":    f"{_PROD}/ftf-ai-api/v1",
        "FTF_ORDER_URL":       f"{_PROD}/order",
        "FTF_SITE_BASE_URL":   _PROD,
        "FTF_PORTAL_BASE_URL": _PROD,
        "FTF_BOOKS_BASE_URL":  _PROD,
        "LOG_LEVEL":           "INFO",
        "INVOICE_BATCH_SIZE":  "10",
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
