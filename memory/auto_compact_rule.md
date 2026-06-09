# Auto-Compact Rule

## Purpose
Prevent context window overflow by automatically compacting before hitting the limit.
Context window = 200,000 tokens. Threshold = 60% = ~120,000 tokens since last compact.

## Two-Layer Defense

### Layer 1 — Inline Awareness (primary)
After EVERY response I give:
- Estimate accumulated tokens since the last compaction (use token_usage.txt daily entries as proxy)
- At 60% (~120,000 tokens): invoke `/compact` immediately via Skill tool — no user prompt needed
- At 45–59% (~90,000–119,000 tokens): note "Context approaching limit — will compact after this task"
- Below 45%: no action

### Layer 2 — Cron Backup (safety net)
A recurring cron fires at :09, :24, :39, :54 past every hour (every 15 minutes).
Prompt: reads token_usage.txt + compact_chat.txt, estimates load, triggers /compact if threshold hit.
Cron is session-bound (up to 7 days). Re-register at every new session start (see below).

## Session Start Behavior (MANDATORY)
At the START of every new session, BEFORE doing anything else:
1. Check if an auto-compact cron is already registered (CronList)
2. If NOT registered: create it immediately with CronCreate
   - cron: "9,24,39,54 * * * *"
   - durable: true
   - recurring: true
   - prompt: (see Cron Prompt below)
3. Confirm cron is active, then proceed with the session

## Cron Prompt (use exactly)
```
Auto-compact check (FTF project). 

Read token_usage.txt at path: c:\Users\Prateek Chandra\OneDrive - NexGen Enterprises\Claude\Agentic AI\FTF- Survey Invoicing & Billing Delivery (E2E)\token_usage.txt

Read compact_chat.txt at path: c:\Users\Prateek Chandra\OneDrive - NexGen Enterprises\Claude\Agentic AI\FTF- Survey Invoicing & Billing Delivery (E2E)\compact_chat.txt

1. From token_usage.txt: sum all token totals from today's date block entries that appear AFTER the last compact entry in compact_chat.txt. This is the estimated tokens since last compaction.

2. If estimated tokens >= 120,000: invoke /compact immediately.

3. If estimated tokens is between 90,000 and 119,999: output a warning "⚠️ Context at ~XX% — compact soon" but do not compact yet.

4. If below 90,000: output "Context OK (~XX,XXX tokens since last compact)" and stop.
```

## Token Estimation Guide
- Each entry in token_usage.txt has a Total column
- Sum all "Total" values since the last /compact timestamp in compact_chat.txt
- That sum = estimated tokens consumed since last compaction
- 120,000 / 200,000 = 60% threshold

## Notes
- Cron jobs survive up to 7 days per session even with durable:true
- This memory rule ensures permanent behavior across all sessions
- The compact itself updates compact_chat.txt automatically (see CLAUDE.md rule)
