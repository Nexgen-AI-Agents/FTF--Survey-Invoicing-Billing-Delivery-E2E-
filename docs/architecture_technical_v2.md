# FTF Agentic AI — Technical Architecture
**Sprint 11 — Invoice Pipeline**
Last updated: 2026-06-03

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SYSTEMS                            │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐   │
│  │  FTF Track Flow  │  │  nesa@nexgen     │  │  MS Teams       │   │
│  │  (Orders + CRM)  │  │  logix.com       │  │  Channel        │   │
│  │  stage.field     │  │  IMAP/SMTP       │  │  Logic App      │   │
│  │  tofinish.jobs   │  │                  │  │  + Graph API    │   │
│  └────────┬─────────┘  └────────┬─────────┘  └──────┬──────────┘   │
└───────────┼─────────────────────┼────────────────────┼─────────────┘
            │                     │                    │
            ▼                     ▼                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   INVOICE PIPELINE (Sprint 11)                      │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  invoice_pipeline.yml — GitHub Actions every 30 min         │   │
│  │  A0 Orchestrator → A1 → A2 → A3 → A4 → A5 → A6 → A7       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  approval_poller.yml — GitHub Actions every 2 min           │   │
│  │  A4 → A5 → A6 (reply check + send only — no discovery)     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Both workflows share concurrency group: invoice-state-write        │
│  (prevents concurrent Excel state writes)                           │
│                                                                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
             ┌─────────────────────────┐
             │  Excel State Store      │
             │  data/invoice_pipeline_ │
             │  state.xlsx             │
             │                         │
             │  data/pipeline_state    │
             │  .json (dashboard)      │
             │                         │
             │  data/learned_rules     │
             │  .json (A7 → A3)        │
             └─────────────────────────┘
```

---

## 2. Agent Map

### All Agents (A0–A7)

| Agent | File | Trigger | Input | Output | LLM |
|-------|------|---------|-------|--------|-----|
| **A0** Orchestrator | `agent_a0_orchestrator.py` | GitHub Actions (30 min) | — | Calls A1–A7 in sequence | No |
| **A1** Flag Hunter | `agent_a1_flag_hunter.py` | via A0 | FTF API `filter_by_flag=invoice_needed` | Excel rows status=`invoice_needed` | No |
| **A2** Data Collector | `agent_a2_data_collector.py` | via A0 | FTF order, IMAP inbox, county appraiser, Google Maps | `data_sources` JSON in Excel | Haiku (packet assembly) |
| **A3** Invoice Compiler | `agent_a3_invoice_compiler.py` | via A0 | `data_sources` packet, `learned_rules.json`, `pricing_examples` sheet | `invoice_draft` JSON, Teams card posted | Sonnet (pricing + reasoning) |
| **A4** Human Gate v2 | `agent_a4_human_gate_v2.py` | Poller (2 min) + A0 (30 min) | Teams thread replies via Graph API | Status → `invoice_approved` / `invoice_rejected` / `on_hold` / `invoice_draft_posted` | Sonnet (NL parse) |
| **A5** Invoice Finalizer | `agent_a5_invoice_finalizer.py` | via A0 + Poller | Approved `invoice_draft` | `POST /invoices` to FTF, `invoice_id` stored | No |
| **A6** Sender v2 | `agent_a6_sender_v2.py` | via A0 + Poller | `invoice_draft`, `customer_email` | SMTP email to client | No |
| **A7** Feedback Learner | `agent_a7_feedback_learner.py` | via A0 | Teams thread replies (non-approval) | `learned_rules.json` updated, Teams acknowledgment | Haiku (rule extraction) |

### Agent Detail Notes

**A1 — Flag Hunter**
- Calls `GET /orders?filter_by_flag=invoice_needed` on FTF API (paginates all results)
- Skips orders already in Excel state
- Creates Excel row with `status=invoice_needed`

**A2 — Data Collector**
- Sources: FTF order API, FTF customer API, IMAP email search, county appraiser URL lookup, Google Maps Static API (aerial)
- Produces structured `packet` JSON with confidence scores per field
- Sets status → `data_collected`; sets `details_missing` if critical fields (email, address) cannot be resolved

**A3 — Invoice Compiler**
- Loads `learned_rules.json` and `pricing_examples` sheet into Claude context
- Calls `_ai_compile_price()` with `max_tokens=2000` and `_MAX_PRICE_RETRIES=2`
  - On JSON parse failure: logs warning and retries (up to 2 additional attempts)
  - On all retries exhausted: returns escalation dict with `escalate_flag=True`, `flags=["ai_error"]`
- Builds `invoice_draft` JSON: services list, amounts, `pricing_reasoning`, `confidence`, `escalate_flag`
- Posts approval card to Teams via Logic App webhook
- Captures `approval_message_id` from Graph API (strict order_id search, 8 retries)
- Sets status → `invoice_draft_posted`

**A4 — Human Gate v2**
- Called both from 2-min poller AND 30-min pipeline
- Calls `GET /teams/{teamId}/channels/{channelId}/messages/{msgId}/replies`
- Self-corrects stale `approval_message_id` via `find_channel_message_for_order()` (scans up to 200 msgs)
- Approved senders: Robert, Ryan, Prateek (checked by name + email + UPN drift fallback)
- Actions: `approve` / `reject` / `hold` / `modify` / `question` / `ignore`
- Stores `processed_reply_ids` in JSON to avoid re-processing
- On `modify`: applies change to draft, increments `modification_count`, reposts card in thread
- On `approve`: optionally captures `email_override_to` (send to approver instead of client)
- Saves every correction as a learning via `save_invoice_learning()`

**A5 — Invoice Finalizer**
- Calls `POST /invoices` on FTF API with draft services + amounts
- Verifies response contains `invoice_id`
- Sets status → `invoice_finalized`

**A6 — Sender v2**
- Sends HTML email via SMTP (TLS port 587); from `nesa@nexgenlogix.com`
- Email routing priority: `EMAIL_OVERRIDE_ALL` → `email_override_to` (in draft) → `customer_email`
- When `EMAIL_OVERRIDE_ALL` is set (TEST MODE): all emails go to that address; client is never notified;
  Teams thread reply confirms: `🧪 TEST MODE — Email redirected to {EMAIL_OVERRIDE_ALL} (client NOT notified).`
- Respects `email_override_to` in draft JSON if approver asked "send to me"
- `SKIP_SEND_DELAY=1` env var (set by approval_poller.yml) bypasses 6–13 min human-like delay
- Posts Teams thread confirmation after send
- Sets status → `invoice_sent`
- **Current status:** SMTP credentials not yet configured — `SMTP_PASSWORD` for `nesa@nexgenlogix.com` is missing
  from both local `.env` and GitHub secrets. Email send will fail with `AgentError: SMTP not configured` until fixed.

**A7 — Feedback Learner**
- Reads all Teams channel messages from last 48h
- Fetches thread replies for messages with reply_count > 0
- Skips APPROVE/REJECT/DEFER commands (those are A4's domain)
- Skips already-processed reply IDs
- Sends remaining feedback to Claude Haiku: "Is this a learnable pricing rule?"
- Saves HIGH/MEDIUM confidence rules to `data/learned_rules.json`
- Posts `[INFO] Learned: ...` acknowledgment in the Teams thread

---

## 3. Order Status State Machine

```
  FTF API (invoice_needed flag detected by A1)
                        │
                        ▼
               invoice_needed
                        │
              A2 runs — enriches order
                        │
              ┌─────────┴──────────┬──────────────────────┐
              │ success            │ partial data          │ hard failure
              ▼                    ▼                       ▼
       data_collected         details_missing         [retry next run]
              │                    │
              │                    └──► [stays here until data found]
     A3 runs — prices + posts Teams card
              │
       invoice_draft_posted  ◄──── A4: modify → repost
              │
     A4 polls thread replies (every 2 min)
              │
    ┌─────────┼──────────┬──────────────────┐
    │         │          │                  │
    ▼         ▼          ▼                  ▼
invoice_   invoice_   on_hold         invoice_needs_
approved  rejected                    human (>5 mods)
    │         │
    │         └──► [end — no email sent]
    │
    ▼
A5 runs — creates FTF invoice
    │
invoice_finalized
    │
A6 runs — sends email to client
    │
invoice_sent ← Phase 1 complete
```

### Status Count Snapshot (2026-06-03)

| Status | Count | Notes |
|--------|-------|-------|
| `invoice_draft_posted` | ~121 | Waiting for Teams approval |
| `invoice_needed` | ~116 | Queued — A2 not yet run |
| `data_collected` | ~80 | A2 done — A3 not yet run |
| `details_missing` | ~61 | Missing email / address |
| `invoice_finalized` | 1 | Test order — will send when SMTP configured |
| `invoice_sent` | 0 | Email delivery blocked (SMTP unconfigured) |

---

## 4. Two-Schedule Architecture

### Why Two Workflows

The pipeline runs on two separate GitHub Actions schedules sharing one concurrency group (`invoice-state-write`):

| Workflow | File | Schedule | Runs | Purpose |
|----------|------|----------|------|---------|
| Invoice Pipeline | `invoice_pipeline.yml` | Every 30 min | A0 → A1→A2→A3→A4→A5→A6→A7 | Full cycle: discover + research + price + check replies + send + learn |
| Approval Poller | `approval_poller.yml` | Every 2 min | A4 → A5 → A6 | Fast reply check only — no discovery overhead |

**Concurrency behavior:**
- Both use group `invoice-state-write`
- Invoice pipeline: `cancel-in-progress: true` (drops stale queued runs)
- Approval poller: `cancel-in-progress: false` (queues, never cancels in-progress)
- Effect: after you reply in Teams, invoice created + email sent within ~2–4 minutes

---

## 5. State Store — Excel

All pipeline state lives in `data/invoice_pipeline_state.xlsx` (committed to git by GitHub Actions bot after each run).

### Sheets

| Sheet | Purpose |
|-------|---------|
| `pipeline_state` | One row per order — full lifecycle state |
| `learnings` | Human corrections saved per order |
| `pending_confirmations` | Multi-order decision state machine |
| `poll_state` | `last_processed_at` timestamp |
| `pricing_examples` | Robert/Ryan-entered pricing examples (A3 lookup) |

### Key columns (pipeline_state)

| Column | Type | Notes |
|--------|------|-------|
| `order_id` | str | Always stored as str — openpyxl int-cast prevented |
| `status` | str | See state machine above |
| `approval_message_id` | str | Teams message ID — stored as str |
| `invoice_draft` | JSON str | Full draft including `email_override_to` if set |
| `processed_reply_ids` | JSON str | List of reply IDs already acted on |
| `approved_by` | str | Sender name who approved |
| `invoice_id` | str | FTF invoice ID after A5 |

### Bot commit conflicts

GitHub Actions bot commits the binary Excel file after every run. Direct `git pull --rebase` conflicts with bot commits. Fix pattern:
```
git rebase --abort
Remove-Item -Recurse -Force ".git\rebase-merge"   # if rebase-merge dir stuck
git reset --hard origin/main
# re-apply local change, then:
git add <file> && git commit -m "..." && git push origin main
```

---

## 6. Teams Integration

### Send (outbound)

All outbound messages go via **Azure Logic App** webhook (`TEAMS_INCOMING_WEBHOOK_URL`).
The Logic App relays the payload to the Teams channel.

| Action | Method | Notes |
|--------|--------|-------|
| Post new approval card | Logic App webhook `POST` | `{"subject": ..., "text": ...}` |
| Post thread reply | Logic App webhook `POST` | Adds `parent_message_id` field |

### Read (inbound)

All inbound reads go via **MS Graph API** (`ChannelMessage.Read.All` application permission).

| Operation | Endpoint |
|-----------|----------|
| Fetch channel messages | `GET /teams/{teamId}/channels/{channelId}/messages?$top=50` |
| Fetch thread replies | `GET /teams/{teamId}/channels/{channelId}/messages/{msgId}/replies?$top=50` |
| Recover message ID for order | Scan up to 200 messages, match `order_id` in body content |

### Auth

- Azure AD app (`TEAMS_APP_ID` + `TEAMS_CLIENT_SECRET`): client credentials grant
- Token cached in-memory, refreshed 60s before expiry
- 401 responses trigger immediate token cache clear + retry

---

## 7. Data Flow — A2 Order Packet

A2 produces a `data_sources` JSON stored in the Excel row. A3 reads it for pricing.

```json
{
  "ftf_order": {
    "order_id": "1000273343",
    "service_type": "Land Survey Only",
    "county": "Volusia County",
    "flood_zone": "ZONE: X",
    "customer_type": "individual",
    "due_amount": 475.0
  },
  "ftf_customer": { "name": "Johanne Beaumont", "email": "..." },
  "emails_found": 0,
  "email_snippets": [],
  "appraiser_data": { "lot_size": "0.12 acres", "legal_description": "..." },
  "aerial_analysis": {},
  "packet": {
    "client_name":        { "value": "Johanne Beaumont", "confidence": "HIGH" },
    "client_email":       { "value": "bacall40@hotmail.com", "confidence": "HIGH" },
    "property_address":   { "value": "152 Woodbridge Cir, Daytona Beach FL", "confidence": "HIGH" },
    "property_county":    { "value": "Volusia County", "confidence": "HIGH" },
    "services_requested": { "value": ["Land Survey Only"], "confidence": "HIGH" },
    "lot_size":           { "value": "0.12 acres", "confidence": "MEDIUM" },
    "client_tier":        { "value": "residential", "confidence": "HIGH" },
    "urgency":            { "value": "normal", "confidence": "MEDIUM" },
    "gaps":               ["Legal description missing"],
    "summary":            "..."
  }
}
```

---

## 8. Pricing Hierarchy (A3)

```
1. learned_rules.json (A7 extractions — highest recency)
   └─ Active rules matching service_type and/or county

2. pricing_examples sheet (Robert/Ryan-entered examples)
   └─ Exact service + exact county → median of recent examples
   └─ Exact service (any county) → median

3. Base rates (from 18,000+ real production orders)
   Land Survey Only:           $475 residential / $617 B2B
   Elevation Certificate:      $225
   Land Survey + EC:           $400
   Commercial (any):           $2,100
   Topographic Survey:         $600
   Default:                    $475

4. Modifiers applied on top of base rate:
   - Lot > 0.31 acres:         +$50
   - Metes & bounds legal:     +$25
   - Monroe County:            +$200
   - Flood zone (non-X):       +$50
   - Pool / waterfront / canal: +$25 each
   - B2B client:               × 1.3
```

### A3 AI Pricing — Reliability Guard

`_ai_compile_price()` in `agent_a3_invoice_compiler.py`:

- `max_tokens=2000` — raised from 800; prevents truncation on complex pricing JSON
- `_MAX_PRICE_RETRIES = 2` — retries twice on JSON parse failure before escalating
- On all retries exhausted: returns `{"escalate_flag": True, "flags": ["ai_error"], ...}` and posts ESCALATED Teams card
- Committed: `43e7326`

---

## 9. Shared Core (`code/shared/`)

| Module | Purpose |
|--------|---------|
| `core/excel_db.py` | Excel state store — all CRUD, str-coercion for ID columns |
| `core/ftf_mysql.py` | Direct MySQL reads for order status (`ng_status`, `ng_status_desc`) |
| `core/teams_graph_client.py` | Logic App webhook (send) + MS Graph API (read) |
| `core/claude_client.py` | Anthropic API wrapper with prompt caching |
| `core/logger.py` | Structured logging |
| `core/exceptions.py` | `AgentError` — catchable pipeline errors |
| `config/settings.py` | All env vars with defaults |
| `config/models.py` | LLM model name constants (Sonnet for A3/A4, Haiku for A2/A7) |

---

## 10. Environment Variables

```
# FTF API
FTF_API_KEY=
FTF_API_BASE_URL=https://stage.fieldtofinish.jobs/ftf-ai-api/v1
FTF_ORDER_URL=https://stage.fieldtofinish.jobs/admin/orders

# MySQL (direct DB reads — A1 flag hunter)
MYSQL_HOST=
MYSQL_PORT=3306
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_DB=

# Anthropic
ANTHROPIC_API_KEY=

# MS Teams
TEAMS_TENANT_ID=
TEAMS_APP_ID=
TEAMS_CLIENT_SECRET=
TEAMS_TEAM_ID=
TEAMS_CHANNEL_ID=
TEAMS_INCOMING_WEBHOOK_URL=    # Logic App HTTP trigger URL

# Email read (A2 context)
IMAP_HOST=outlook.office365.com
IMAP_PORT=993
IMAP_USER=nesa@nexgenlogix.com
IMAP_PASSWORD=

# Email send (A6) — CRITICAL BLOCKER: not yet configured
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=nesa@nexgenlogix.com
SMTP_PASSWORD=                 # ← MISSING — needs password for nesa@nexgenlogix.com
SMTP_FROM=nesa@nexgenlogix.com

# Approvals
APPROVED_SENDERS=robert:robert_e@nexgenlogix.com,ryan:rt@ryantisko.com,prateek:pchandra@nexgen.enterprises
MAX_INVOICE_MODIFICATIONS=5

# Poller behavior
SKIP_SEND_DELAY=1              # Set by approval_poller.yml — bypasses A6 random sleep

# Test mode — when set, ALL invoice emails redirect to this address; client never notified
EMAIL_OVERRIDE_ALL=            # Set as GitHub secret; leave empty in prod to send to real clients

# Optional
GOOGLE_MAPS_API_KEY=
GOOGLE_REVIEW_URL=
DASHBOARD_GITHUB_TOKEN=        # Push pipeline_state.json to public dashboard repo
```

---

## 11. Infrastructure

| Layer | Technology |
|-------|-----------|
| Scheduling | GitHub Actions — 2 workflows, shared concurrency group |
| Runtime | Python 3.11, ubuntu-latest |
| AI models | Claude Sonnet 4.6 (A3 pricing, A4 NL parse), Claude Haiku 4.5 (A2 assembly, A7 rule extraction) |
| State | Excel (`data/invoice_pipeline_state.xlsx`) committed to git by bot |
| Teams send | Azure Logic App HTTP trigger → Teams channel |
| Teams read | MS Graph API v1.0, `ChannelMessage.Read.All` application permission |
| FTF | REST API + direct MySQL read (ng_status_desc) |
| Email read | IMAP SSL port 993 |
| Email send | SMTP TLS port 587 — **not yet active; SMTP_PASSWORD missing** |
| Repo | `Nexgen-AI-Agents/FTF--Survey-Invoicing-Billing-Delivery-E2E-` (private) |

---

## 12. Known Gaps / Pending Actions

| # | Item | Owner | Blocker? |
|---|------|-------|----------|
| 1 | `SMTP_PASSWORD` for `nesa@nexgenlogix.com` — add to `.env` + GitHub secrets | Prateek | **Yes — no emails can send** |
| 2 | Rotate `FTF_API_KEY` — currently exposed in git history; remove from tracked files | Prateek | No (security hygiene) |
| 3 | Reply to Teams card for order 1000271787 (ESCALATED — ai_error) with correct price | Robert/Ryan/Prateek | No |
| 4 | Mark's GitHub Outside Collaborator access — review if he should still receive Actions failure emails | Prateek | No |
