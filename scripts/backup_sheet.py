"""Back up the live OneDrive Approvals workbook to the server.

Downloads the authoritative OneDrive workbook (the sheet the client edits) and writes it
to <deploy>/backups/:
  - latest.xlsx                      — always the most recent copy
  - Approvals_backup_<UTC>.xlsx      — timestamped snapshot (rolling; keeps the newest N)

Invoked by the server wrappers (run_server_pipeline.sh / run_server_watcher.sh) at the END
of every cycle, so the backup tracks the sheet on every update. READ-ONLY with respect to
the live sheet — it only downloads; it never writes to, deletes from, or reorders the sheet.

Safe to run standalone:  python scripts/backup_sheet.py
"""
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from core.onedrive_excel_client import _download_workbook_bytes, upload_backup_copy  # noqa: E402
from core.logger import get_logger  # noqa: E402

log = get_logger("backup_sheet")

REPO_ROOT   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKUP_DIR  = os.path.join(REPO_ROOT, "backups")
KEEP             = int(os.getenv("SHEET_BACKUP_KEEP", "2016"))            # rolling snapshots kept
MIN_INTERVAL_MIN = int(os.getenv("SHEET_BACKUP_MIN_INTERVAL_MIN", "30"))  # do a real backup at most every N min
# At 30-min cadence, KEEP=2016 ≈ 42 days of history. The wrappers still invoke this every
# cycle, but the throttle below skips work unless MIN_INTERVAL_MIN has elapsed — this keeps
# OneDrive version history + local snapshots from churning. Pass --force to override.


def _prune(dir_path: str, keep: int) -> None:
    """Keep only the newest `keep` timestamped snapshots; never touch latest.xlsx."""
    snaps = sorted(
        f for f in os.listdir(dir_path)
        if f.startswith("Approvals_backup_") and f.endswith(".xlsx")
    )
    for old in snaps[:-keep] if keep > 0 else []:
        try:
            os.remove(os.path.join(dir_path, old))
        except OSError as exc:
            log.warning("could not remove old backup %s: %s", old, exc)


def _recent_backup_within(dir_path: str, interval_min: int) -> bool:
    """True if a snapshot was written less than interval_min ago (throttle guard)."""
    if interval_min <= 0:
        return False
    snaps = [os.path.join(dir_path, f) for f in os.listdir(dir_path)
             if f.startswith("Approvals_backup_") and f.endswith(".xlsx")]
    if not snaps:
        return False
    newest = max(os.path.getmtime(p) for p in snaps)
    return (time.time() - newest) < interval_min * 60


def main() -> int:
    force = "--force" in sys.argv[1:]
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if not force and _recent_backup_within(BACKUP_DIR, MIN_INTERVAL_MIN):
        log.info("sheet backup throttled — last snapshot < %d min ago (use --force to override)",
                 MIN_INTERVAL_MIN)
        return 0
    try:
        data = _download_workbook_bytes()
    except Exception as exc:  # never fail the pipeline because a backup hiccuped
        log.warning("sheet backup skipped — download failed: %s", exc)
        return 0

    if not data:
        log.warning("sheet backup skipped — empty download")
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snapshot = os.path.join(BACKUP_DIR, f"Approvals_backup_{stamp}.xlsx")
    latest   = os.path.join(BACKUP_DIR, "latest.xlsx")

    with open(snapshot, "wb") as fh:
        fh.write(data)
    with open(latest, "wb") as fh:
        fh.write(data)

    _prune(BACKUP_DIR, KEEP)
    log.info("sheet backup written: %s (%d bytes) + latest.xlsx", os.path.basename(snapshot), len(data))

    # Mirror the full workbook to a separate OneDrive backup file so it's reachable via a
    # stable shareable URL. Never touches the live sheet. A failure here is non-fatal.
    try:
        url = upload_backup_copy(data)
        if url:
            with open(os.path.join(BACKUP_DIR, "BACKUP_URL.txt"), "w", encoding="utf-8") as fh:
                fh.write(url + "\n")
            log.info("OneDrive backup copy updated: %s", url)
            print(f"BACKUP_URL={url}")
    except Exception as exc:
        log.warning("OneDrive backup copy skipped — upload failed: %s", exc)

    return 0


if __name__ == "__main__":
    sys.exit(main())
