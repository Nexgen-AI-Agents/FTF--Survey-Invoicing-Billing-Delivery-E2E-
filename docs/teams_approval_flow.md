# Teams Approval Flow — Rules, Commands & Edge Cases

> **AI instruction:** Read this file whenever working on anything related to Teams approval/rejection,
> `poll_teams_approvals.py`, `send_daily_approval_reminder.py`, `teams_graph_client.py`,
> `agent_04_human_gate.py`, or any command parsing / confirmation flow logic.

---

## Approved Senders (Whitelist)

Only the following people can approve or reject estimates via Teams.
Matched on first name, case-insensitive (e.g. "Robert Ellis" matches "robert").

| Name | First-name key |
|------|----------------|
| Robert | robert |
| Ryan | ryan |
| Prateek | prateek |

Configured via `APPROVED_SENDERS` env var (default: `robert,ryan,prateek`).
Unauthorized senders get a `[WARNING]` message posted to the channel. No action taken.

---

## Supported Commands

All commands can be typed as a **reply to a notification thread** OR directly in the channel.
Comma, space, or mixed separators all work for order IDs.

| Command | Behavior |
|---------|----------|
| `APPROVE` | Auto-approve the single pending order. If 0 or multiple → warn. |
| `APPROVE ALL` | Approve every pending order (pre-confirm + post-confirm). |
| `APPROVE <id>` | Approve one specific order. |
| `APPROVE <id1>, <id2>` | Approve multiple (comma or space separated). |
| `REJECT` | Auto-reject the single pending order. If 0 or multiple → warn. |
| `REJECT ALL [reason]` | Reject every pending order with optional reason. |
| `REJECT <id> [reason]` | Reject one order with optional reason. |
| `REJECT <id1>, <id2> [reason]` | Reject multiple; trailing words after last ID = reason. |

**Mixed commands in one message are supported:**
`APPROVE QA-001, QA-002 REJECT QA-003 bad scope` → approves 2, rejects 1.

---

## Order ID Validation

Each token after APPROVE / REJECT is checked to see if it looks like a real order ID:
- Contains at least one digit → valid ID token (e.g. `1000276115`)
- Contains a hyphen → valid ID token (e.g. `QA-LIVE-TEST-001`)
- 5+ chars starting with uppercase → valid ID token
- Short lowercase English words (of, this, it, etc.) → filtered out as conversational text

---

## Actionable Statuses

| Action | Statuses that can be actioned immediately |
|--------|------------------------------------------|
| APPROVE | `awaiting_approval`, `flagged`, `priced` |
| REJECT | `awaiting_approval`, `flagged`, `priced` |

Orders in any other status (e.g. `sent`, `on_hold`) cannot be actioned — bot warns.

---

## Decision Reversal (Confirmation Required)

If someone tries to reverse a final decision (approve an already-rejected order,
or reject an already-approved order), the bot **does not process immediately**.
It posts a YES/NO confirmation request and waits.

### Flow

```
User: REJECT QA-001        (QA-001 is currently "approved")
Bot:  "QA-001 was APPROVED. Change to REJECTED? Reply YES or NO."
      → saves to pending_confirmations.json (TTL = 24h)

User: yeah / yep / go ahead / do it / sure
Bot:  "Robert confirmed. Changing QA-001 from approved → rejected..."
      → processes rejection
      → posts "[REJECTED] Decision changed: QA-001 → rejected."

OR

User: nope / nah / keep it / cancel
Bot:  "Decision kept as APPROVED for QA-001. No change made."
```

### YES Synonyms
`yes, yeah, yep, yup, sure, ok, okay, confirm, confirmed, absolutely, definitely,
proceed, affirmative, correct, do it, go ahead, go for it, yes please, change it`

### NO Synonyms
`no, nope, nah, cancel, stop, negative, abort, skip, dont, don't, keep,
keep it, never mind, no change, leave it, no thanks, don't change`

### Rules
- Can repeat indefinitely — each flip cycle requires a new confirmation.
- Confirmation expires after **24 hours** with no response. Bot posts "expired — re-submit."
- Both original decision AND override are logged in `agent_decision_log` with timestamp and sender.
- State stored in `scripts/pending_confirmations.json` (auto-created on first use).

---

## Multiple Users — Same Order

| Scenario | Behavior |
|----------|----------|
| Ryan approves → Robert also approves | Second attempt: `[WARNING] already approved` |
| Ryan approves → Robert rejects | Triggers reversal confirmation flow (above) |
| Ryan approves → Robert approves again | `[WARNING] already approved` — no action |
| Two users approve at exact same time | DB write is atomic — first write wins, second warns |

---

## Random Conversation in Thread

The bot **only responds to APPROVE / REJECT keywords**.
All other messages in a thread are silently ignored.

Examples that do NOT trigger the bot:
- "This looks expensive"
- "I approve of this design"  ← "approve" present but "of", "this", "design" are not order IDs
- "Let me check with Robert"
- "Yeah, looks good" ← "yeah" alone without a pending confirmation is ignored

---

## No Reply by End of Day

If orders remain in `awaiting_approval` or `flagged` for more than **12 hours**
without any decision, the bot sends a daily reminder.

### Daily Reminder (I-086)
- **Schedule:** Every weekday at 9:00 AM ET via GitHub Actions (`approval_reminder.yml`)
- **Script:** `scripts/send_daily_approval_reminder.py`
- **Content:** All leftover orders with original pending-since timestamp, age label,
  service, estimate, FTF link, and full command examples
- **Repeats:** Every working day until a decision is made
- **Sorted:** Oldest-first so most overdue orders appear at top

---

## Still-Pending Summary (After Each Poll Cycle)

After any approval or rejection is processed, if other orders remain pending,
the bot posts a **top-level channel message** (never buried in a thread):

> [INFO] **3 order(s) still pending — action required:**
> &nbsp;&nbsp;QA-LIVE-TEST-A03a
> &nbsp;&nbsp;QA-LIVE-TEST-B01
> &nbsp;&nbsp;QA-LIVE-TEST-C02

This ensures pending orders are always visible in the channel feed regardless
of which thread the user was replying to.

---

## Poll State

Last-processed timestamp stored in two places (for redundancy):
- **Primary:** `loop_state` DB table (key: `poll_teams_approvals`)
- **Fallback:** `scripts/poll_state.json`

---

## Key Files

| File | Purpose |
|------|---------|
| `scripts/poll_teams_approvals.py` | Main poll loop — runs on demand or cron |
| `scripts/send_daily_approval_reminder.py` | Daily 9 AM leftover reminder |
| `scripts/pending_confirmations.json` | Runtime state for pending YES/NO confirmations |
| `scripts/poll_state.json` | Fallback for last-processed timestamp |
| `code/shared/core/teams_graph_client.py` | All Teams API calls, command parsing |
| `code/sprint_03_human_gate/agents/agent_04_human_gate.py` | `process_approval_reply()` |
| `.github/workflows/approval_reminder.yml` | GitHub Actions daily reminder schedule |

---

## Related Issues

| Issue | Summary |
|-------|---------|
| I-083 | Teams inbound approval mechanism built |
| I-086 | Daily leftover reminder — CLOSED |
| I-087 | Decision reversal confirmation state machine — CLOSED |
| I-088 | Multiple users same order — first wins, reversal requires confirmation — CLOSED |
| I-089 | Random chat in thread safely ignored — CLOSED |
