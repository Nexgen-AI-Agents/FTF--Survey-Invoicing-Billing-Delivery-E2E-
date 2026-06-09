# Auto-Compact Rule

## Policy (Updated 2026-06-09)

/compact is triggered **manually by Prateek only** — never automatically.

When Prateek runs /compact, update compact_chat.txt with a new entry:
- Time (ET)
- Tokens before / after / freed / saved (estimated)
- Context state summary
- Update CUMULATIVE SUMMARY table

No cron. No auto-trigger. No session-start CronCreate.
