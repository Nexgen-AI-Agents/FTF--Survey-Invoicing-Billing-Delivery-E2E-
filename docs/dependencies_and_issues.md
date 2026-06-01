# Dependencies, Critical Issues & Missing Gaps
**Sprint 11 — Invoice Pipeline**
Last updated: 2026-06-01

---

## PART 1 — DEPENDENCIES ON PRATEEK
> These are hard blockers. The pipeline **will not run** until each one is resolved.

---

### DEP-01 — GitHub Secrets (8 new secrets required)
**Owner:** Prateek | **Status:** Pending

Go to: `GitHub repo → Settings → Secrets and variables → Actions → New repository secret`

| Secret Name | Value | Notes |
|-------------|-------|-------|
| `TEAMS_CHAT_ID` | `19:b88d010aa8254609937c512aded09e5f@thread.v2` | Already known — just add it |
| `IMAP_HOST` | e.g. `outlook.office365.com` | Check what mail server hosts nesa@nexgenlogix.com |
| `IMAP_PORT` | `993` | SSL port — confirm with your mail provider |
| `IMAP_USER` | `nesa@nexgenlogix.com` | The mailbox we read for order details |
| `IMAP_PASSWORD` | (mailbox app password) | Use app password if 2FA enabled |
| `SMTP_HOST` | e.g. `smtp.office365.com` | For sending invoices via A6 |
| `SMTP_PORT` | `587` | TLS port — confirm with provider |
| `SMTP_USER` | `nesa@nexgenlogix.com` | Sending address |
| `SMTP_PASSWORD` | (mailbox app password) | Same or different as IMAP password |
| `SMTP_FROM` | `nesa@nexgenlogix.com` | Must override current default `statements@nexgensurveying.com` |

---

### DEP-02 — Azure AD Permissions (2 new scopes)
**Owner:** Prateek | **Status:** Pending

The existing Azure AD app registration (same one used for Teams approvals) needs two NEW application permissions granted with admin consent:

| Permission | Type | Reason |
|------------|------|--------|
| `Chat.Read.All` | Application | A4 needs to READ replies in the group chat |
| `Chat.ReadWrite.All` | Application | A3 needs to POST invoice drafts to the group chat |

Steps:
1. Azure Portal → Azure Active Directory → App registrations → your app
2. API permissions → Add a permission → Microsoft Graph → Application permissions
3. Add `Chat.Read.All` and `Chat.ReadWrite.All`
4. Click "Grant admin consent for [your tenant]"

**Note:** The existing `ChannelMessage.Read.All` permission (for channel reading) does NOT cover group chats — these are different APIs.

---

### DEP-03 — Run DB Migration
**Owner:** Prateek | **Status:** Pending

**Must run before the first pipeline trigger.** Without this, agents A2–A6 crash immediately (columns don't exist yet).

```bash
psql -h <DB_HOST> -U <DB_USER> -d ftf_agentic_ai -f code/migrations/002_invoice_pipeline.sql
```

What it adds:
- 10 new columns on `processed_orders`: `invoice_draft`, `data_sources`, `approval_message_id`, `modification_count`, `invoice_id`, `client_name`, `property_address`, `data_collected_at`, `draft_posted_at`, `invoice_created_at`
- New table `invoice_learnings` (stores all human corrections for AI learning)
- 3 indexes for fast status queries

---

### DEP-04 — FTF API Confirmation (2 questions for Ryan/FTF dev)
**Owner:** Prateek → Ryan | **Status:** Pending

**Q1: Does creating an invoice via `POST /invoices` automatically clear the `invoice_needed` flag?**
- If YES → A5 is complete as-is.
- If NO → I need to add a PATCH call in A5 to explicitly clear it. Tell me and I'll add it in 5 minutes.

**Q2: What exact JSON fields does `POST /invoices` require?**
Current code sends: `{order_id, amount, services: [{name, description, amount}]}`
If the field names are different in FTF, A5 will get a 400/422 error.
- Ask Ryan or check the FTF API docs for the `/invoices` endpoint schema.

---

### DEP-05 — Confirm App Added to Teams Group Chat
**Owner:** Prateek | **Status:** Pending

The app registration (`Chat.ReadWrite.All` permission) can only post to a chat if the app (or a bot linked to it) **has been added as a member** of that specific group chat.

Steps:
- Open the group chat `19:b88d010aa8254609937c512aded09e5f@thread.v2` in Teams
- Add the Azure AD app/bot as a member
- Or confirm with Ryan whether this is already done

If not added, A3's `post_chat_message()` call will return HTTP 403.

---

### DEP-06 — Phone Number in Email Signature
**Owner:** Prateek | **Status:** Quick fix

[agent_a6_sender_v2.py:49](../code/sprint_11_invoice_pipeline/agents/agent_a6_sender_v2.py) has a placeholder:
```
Phone: (555) 000-0000
```
Should be: `(561) 508-6272`
I'll fix it the moment you confirm — just say "fix phone" and it's done.

---

## PART 2 — CRITICAL ISSUES
> Code-level bugs found during review. Severity: BLOCKER / CRITICAL / MAJOR.

---

### I-100 | BLOCKER | A4 Reply Re-Processing Bug

**File:** [agent_a4_human_gate_v2.py](../code/sprint_11_invoice_pipeline/agents/agent_a4_human_gate_v2.py)

**Problem:** A4 polls all thread replies every 15 minutes but has no memory of which replies were already processed. On the second poll cycle:
- The original "APPROVE" reply is still in the thread
- A4 tries to approve the order again
- If the order is already `invoice_approved`, the DB update is idempotent — but A4 also calls `post_chat_reply()` again, sending a second "Invoice approved" confirmation to Teams

**Also:** After a modification, A4 saves draft and resets status to `invoice_draft_posted`. On next poll, A4 re-reads ALL replies including the original modification request and re-applies the modification again. Infinite modification loop.

**Fix needed:** Store `last_processed_reply_id` and `last_processed_at` in `processed_orders`. Only process replies newer than the last-processed timestamp.

---

### I-101 | BLOCKER | DB Migration Not Run — All A2+ Agents Will Crash

**File:** [migrations/002_invoice_pipeline.sql](../code/migrations/002_invoice_pipeline.sql)

**Problem:** The migration hasn't been run yet. Columns `invoice_draft`, `data_sources`, `approval_message_id`, etc. don't exist. Every call to `save_order_state()` with these columns will raise a PostgreSQL error and crash the agent.

**Fix:** Run the migration (DEP-03 above). This is a pure environment issue, not a code bug.

---

### I-102 | CRITICAL | SMTP_FROM Default Is Wrong

**File:** [settings.py:79](../code/shared/config/settings.py)

**Problem:**
```python
SMTP_FROM: str = os.getenv("SMTP_FROM", "statements@nexgensurveying.com")
```
The default falls back to the old statements email. If `SMTP_FROM` secret is not set in GitHub, all invoice emails go out with the wrong FROM address.

**Fix:** Change default to `nesa@nexgenlogix.com`. One-line edit — ready to do immediately.

---

### I-103 | CRITICAL | A2 IMAP Fetches ALL Emails, Then Filters Client-Side

**File:** [agent_a2_data_collector.py:_fetch_matching_emails](../code/sprint_11_invoice_pipeline/agents/agent_a2_data_collector.py)

**Problem:** Current code fetches every email since 90 days ago (potentially thousands), downloads the full body of each, then does client-side text matching. For an active inbox:
- Slow (could time out in a 15-min GitHub Actions job)
- High IMAP bandwidth
- Risk of partial match returning wrong emails

**Fix needed:** Use IMAP `SEARCH TEXT "property address"` or `SEARCH OR SUBJECT "address" BODY "address"` to pre-filter server-side. I can update this immediately.

---

### I-104 | CRITICAL | A2 Teams Search Limited to 200 Most Recent Messages

**File:** [agent_a2_data_collector.py:_fetch_matching_teams_messages](../code/sprint_11_invoice_pipeline/agents/agent_a2_data_collector.py)

**Problem:** `get_chat_messages(limit=200)` only fetches the 200 most recent messages. If the team discussed an order more than 200 messages ago (orders often sit in queue for days/weeks), A2 misses the context entirely.

**Fix needed:** Add pagination — if no match in first 200, fetch next page. Or add a `$search` filter on Graph API (limited support for chats but worth trying).

---

### I-105 | MAJOR | No Idempotency Guard Between GitHub Actions Runs

**File:** [agent_a0_orchestrator.py](../code/sprint_11_invoice_pipeline/agents/agent_a0_orchestrator.py)

**Problem:** GitHub Actions triggers every 15 minutes. If a pipeline run takes >15 minutes (possible when processing multiple orders), a second run starts while the first is still running. Both try to process the same `invoice_needed` orders → race condition → duplicate Teams messages, duplicate invoice creation.

**Fix needed:** Add a PostgreSQL advisory lock at orchestrator startup. Or add a `processing` status that A1 sets immediately when it picks up an order.

---

### I-106 | MAJOR | A4 Orchestrator Path Setup May Fail in GitHub Actions

**File:** [agent_a0_orchestrator.py](../code/sprint_11_invoice_pipeline/agents/agent_a0_orchestrator.py)

**Problem:** The orchestrator does `from agents.agent_a1_flag_hunter import run as run_a1` but each agent file does `sys.path.insert(0, "../../shared")`. When invoked as `python -m agents.agent_a0_orchestrator` from `code/sprint_11_invoice_pipeline/`, the shared path resolves correctly. But the agents also need `config/` and `core/` — those relative paths depend on CWD.

**Fix needed:** Test the exact GitHub Actions `run:` command locally before enabling. The workflow currently does `cd code/sprint_11_invoice_pipeline && python -m agents.agent_a0_orchestrator` — verify this resolves all imports correctly.

---

### I-107 | MAJOR | A5 Fails Silently If FTF Returns No Invoice ID

**File:** [agent_a5_invoice_finalizer.py](../code/sprint_11_invoice_pipeline/agents/agent_a5_invoice_finalizer.py)

**Problem:** After `create_invoice()`, if FTF returns a 200 OK but with no `invoice_id` or `id` field (or uses a different field name), `invoice_id` is stored as empty string `""`. A5 doesn't fail — it advances to `invoice_finalized` with an empty invoice_id. A6 then sends the email without a valid invoice reference.

**Fix needed:** Add a check: `if not invoice_id: raise AgentError(...)` before marking the order finalized.

---

## PART 3 — MISSING GAPS
> Functionality not yet implemented. Will need building before full production.

---

### GAP-01 | Reply Tracking Table (Needed NOW before first live run)

**What's missing:** No record of which Teams reply IDs have been processed by A4. Required to fix I-100.

**Solution:** Add `processed_reply_ids` column (TEXT — comma-separated or JSON array) to `processed_orders`, or create a new `processed_chat_replies` table. Update A4 to:
1. Load already-processed reply IDs before fetching replies
2. Skip replies already in the list
3. After processing, add the reply ID to the list

---

### GAP-02 | Error Notification to Teams

**What's missing:** When any agent crashes (exception not caught at top level), the error goes silently to GitHub Actions logs. Robert/Ryan/Prateek have no idea an order is stuck.

**Solution:** Wrap each agent call in the orchestrator with a try/except that posts a red Teams alert: "⚠️ Agent A2 failed for order X — check GitHub Actions logs. Order is stuck."

---

### GAP-03 | Retry Counter for Failed Orders

**What's missing:** If A2 fails for an order (IMAP down, Teams API error), the order stays at `invoice_needed` forever. Next cycle picks it up again, fails again, indefinitely.

**Solution:** Add `retry_count` increment on failure (column already exists in `processed_orders`). After 3 failures → set status to `invoice_error` and notify Teams.

---

### GAP-04 | `.env.template` for Sprint 11 Variables

**What's missing:** No `.env.template` file shows the new Sprint 11 secrets. Anyone setting up the pipeline fresh has no guide.

**Solution:** Add to existing `.env.template`:
```
TEAMS_CHAT_ID=19:xxxx@thread.v2
IMAP_HOST=outlook.office365.com
IMAP_PORT=993
IMAP_USER=nesa@nexgenlogix.com
IMAP_PASSWORD=
SMTP_FROM=nesa@nexgenlogix.com
MAX_INVOICE_MODIFICATIONS=5
```

---

### GAP-05 | FTF Flag Clear Verification

**What's missing:** After A5 creates the invoice, there's no check that the `invoice_needed` flag was actually cleared in FTF. If the flag persists, A1 will re-queue the same order next cycle, A2 will re-collect, A3 will re-post a duplicate draft to Teams.

**Solution:** After `create_invoice()`, call `get_invoice_needed_orders()` and confirm this order_id is no longer in the result. If still present, flag for manual review.

---

### GAP-06 | Shadow Mode (I-096 — still open)

**What's missing:** AI should run alongside humans without sending — post suggestions to Teams, compare at end of day.

**Status:** Deferred to Sprint 12. Do not build yet — but DO NOT forget.

---

### GAP-07 | MS Graph Email Search (Upgrade from IMAP)

**What's missing:** A2 uses IMAP to search emails. If `nesa@nexgenlogix.com` is on Microsoft 365 (same tenant as Teams), MS Graph `/users/{email}/messages?$search="address"` is faster, supports server-side search, and uses the same auth token already in use.

**Solution:** Add Graph-based email search as primary in A2, IMAP as fallback. Requires `Mail.Read` application permission on the Azure AD app.

---

### GAP-08 | A6 Email Personalization Depth

**What's missing:** Currently personalizes by first name only. Ryan said (2026-05-29): "Include 1 upsell offer." Not yet implemented in A6.

**Solution:** After Phase 1 is stable, add upsell logic to A6 based on service type. Example: Land Survey Only → "Considering adding an Elevation Certificate? We can often schedule it on the same field visit."

---

## Priority Order (What to fix first)

| # | Action | Who | When |
|---|--------|-----|------|
| 1 | Fix I-100 (reply re-processing) | Claude | Now — tell me and I'll code it |
| 2 | Fix I-102 (SMTP_FROM default) | Claude | 1 line — tell me |
| 3 | Fix DEP-06 (phone number) | Claude | 1 line — tell me |
| 4 | Run DEP-03 (DB migration) | Prateek | Before first run |
| 5 | Add DEP-01 (GitHub Secrets) | Prateek | Before first run |
| 6 | Grant DEP-02 (Azure AD perms) | Prateek | Before first run |
| 7 | Answer DEP-04 (FTF API questions) | Prateek → Ryan | Before first run |
| 8 | Confirm DEP-05 (app in chat) | Prateek | Before first run |
| 9 | Fix I-103 (IMAP search improvement) | Claude | Sprint 11 QA |
| 10 | Fix I-104 (Teams pagination) | Claude | Sprint 11 QA |
| 11 | Fix I-105 (idempotency guard) | Claude | Before prod go-live |
| 12 | Build GAP-01 (reply tracking) | Claude | With I-100 fix |
| 13 | Build GAP-02 (error notifications) | Claude | Sprint 11 QA |
| 14 | Build GAP-03 (retry counter) | Claude | Sprint 11 QA |
