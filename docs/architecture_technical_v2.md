# FTF Agentic AI OS — Technical Architecture v2
**Sprint 11 — Invoice Pipeline**
Last updated: 2026-06-01

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SYSTEMS                                │
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  FTF Track Flow  │  │  nesa@nexgen     │  │  MS Teams Group Chat │  │
│  │  (Orders + CRM)  │  │  logix.com       │  │  (Approvals + Comms) │  │
│  │  stage.field     │  │  IMAP/SMTP       │  │  19:b88d...@thread.v2│  │
│  │  tofinish.jobs   │  │                  │  │  MS Graph API        │  │
│  └────────┬─────────┘  └────────┬─────────┘  └──────────┬───────────┘  │
│           │                     │                        │              │
└───────────┼─────────────────────┼────────────────────────┼──────────────┘
            │                     │                        │
            ▼                     ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      INVOICE PIPELINE (Sprint 11)                       │
│                                                                          │
│  GitHub Actions (every 15 min) → agent_a0_orchestrator.py              │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                                                                    │  │
│  │  A1 Flag Hunter ──► A2 Data Collector ──► A3 Invoice Compiler     │  │
│  │       │                    │                      │               │  │
│  │   FTF API              FTF + IMAP            Claude AI +          │  │
│  │  filter_by_flag=        + Teams              pricing_examples     │  │
│  │  invoice_needed         (3 sources)           + post to Teams     │  │
│  │                                                      │            │  │
│  │                              ┌───────────────────────┘            │  │
│  │                              ▼                                    │  │
│  │                    A4 Human Gate v2 ◄──── Teams thread replies    │  │
│  │                    (NL loop, learn,        from Robert/Ryan/      │  │
│  │                     modify, store)         Prateek                │  │
│  │                              │                                    │  │
│  │               ┌──────────────┴──────────────┐                    │  │
│  │               │ approved        rejected     │                    │  │
│  │               ▼                 ▼            │                    │  │
│  │     A5 Invoice Finalizer     [STOP]          │                    │  │
│  │      POST /invoices                          │                    │  │
│  │      verify flag cleared                     │                    │  │
│  │               │                              │                    │  │
│  │               ▼                              │                    │  │
│  │     A6 Sender v2                             │                    │  │
│  │      SMTP email to client                    │                    │  │
│  │      Phase 1 complete                        │                    │  │
│  │                                              │                    │  │
│  └──────────────────────────────────────────────┘                    │  │
│                                                                          │
└──────────────────────────────────────┬──────────────────────────────────┘
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │   PostgreSQL DB       │
                            │   ftf_agentic_ai      │
                            │                       │
                            │  processed_orders     │
                            │  invoice_learnings    │
                            │  pricing_examples     │
                            │  agent_decision_log   │
                            │  loop_state           │
                            └──────────────────────┘
```

---

## 2. Component Map

### 2.1 Agents

| Agent | File | Trigger | Inputs | Outputs | LLM? |
|-------|------|---------|--------|---------|------|
| A0 Orchestrator | `agent_a0_orchestrator.py` | GitHub Actions (15 min) | — | Calls A1–A6 in sequence | No |
| A1 Flag Hunter | `agent_a1_flag_hunter.py` | via A0 | FTF API `filter_by_flag=invoice_needed` | `processed_orders` rows (status=invoice_needed) | No |
| A2 Data Collector | `agent_a2_data_collector.py` | via A0 | FTF order, IMAP inbox, Teams chat (200 msgs) | `data_sources` JSON in DB | Claude Haiku (classification) |
| A3 Invoice Compiler | `agent_a3_invoice_compiler.py` | via A0 | `data_sources` packet, `pricing_examples` DB | `invoice_draft` JSON, Teams message posted | Claude Sonnet |
| A4 Human Gate v2 | `agent_a4_human_gate_v2.py` | via A0 (every cycle) | Teams thread replies | Status update + `invoice_learnings` record | Claude Sonnet |
| A5 Invoice Finalizer | `agent_a5_invoice_finalizer.py` | via A0 | Approved `invoice_draft` | FTF invoice created, `invoice_id` stored | No |
| A6 Sender v2 | `agent_a6_sender_v2.py` | via A0 | `invoice_draft`, `customer_email` | SMTP email to client | No |

### 2.2 Shared Core (`code/shared/`)

| Module | Purpose |
|--------|---------|
| `core/ftf_client.py` | FTF REST API — orders, invoices, customers, pricing |
| `core/teams_graph_client.py` | MS Graph — channel read/write + CHAT read/write (new) |
| `core/db.py` | PostgreSQL CRUD — all state, decisions, learnings |
| `core/claude_client.py` | Anthropic API wrapper with prompt caching |
| `core/hermes_client.py` | Ollama local LLM (hermes3) — low-cost classification |
| `core/logger.py` | Structured logging with PII masking |
| `core/refund_guard.py` | Hard rule — refund → Jessica immediately, AI stops |
| `config/settings.py` | All env vars with defaults |
| `config/models.py` | LLM model name constants |

---

## 3. State Machine — Order Lifecycle

```
                   FTF API ($ flag detected)
                              │
                              ▼
                      invoice_needed           ← A1 sets this
                              │
                  A2 runs (FTF + email + Teams)
                              │
                        ┌─────┴──────┐
                        │ success    │ failure (3x)
                        ▼            ▼
                  data_collected   invoice_error → Teams alert
                        │
                  A3 runs (compile + post to Teams)
                        │
                  invoice_draft_posted          ← A3 sets this
                        │
                  A4 polls every 15 min for replies
                        │
          ┌─────────────┼─────────────┬──────────────────┐
          │             │             │                  │
          ▼             ▼             ▼                  ▼
    invoice_        invoice_     invoice_draft_    invoice_needs_
    approved       rejected       posted           human
          │             │        (A3 reposts        (>MAX mods)
          │             │         updated draft)
          ▼             │
    A5 runs             └──► [end — no email sent]
   (write to FTF)
          │
    invoice_finalized
          │
    A6 runs (send email)
          │
    invoice_sent ← Phase 1 Complete
```

---

## 4. Data Flow — Order Packet

A2 produces a structured JSON `data_sources` blob stored in `processed_orders.data_sources`:

```json
{
  "ftf_order": { "order_id": "...", "service_type": "...", "county": "...", ... },
  "ftf_customer": { "name": "...", "email": "...", ... },
  "emails_found": 2,
  "teams_found": 1,
  "email_snippets": [{"from": "...", "subject": "...", "date": "..."}],
  "teams_snippets": [{"sender": "...", "date": "..."}],
  "packet": {
    "client_name":        {"value": "John Smith",            "confidence": "HIGH"},
    "client_email":       {"value": "john@example.com",      "confidence": "HIGH"},
    "property_address":   {"value": "123 Main St, Miami FL", "confidence": "HIGH"},
    "property_county":    {"value": "Miami-Dade",            "confidence": "HIGH"},
    "services_requested": {"value": ["Land Survey Only"],    "confidence": "MEDIUM"},
    "special_requirements": {"value": "",                    "confidence": "LOW"},
    "lot_size_acres":     {"value": null,                    "confidence": "LOW"},
    "property_features":  {"value": {},                      "confidence": "LOW"},
    "client_tier":        {"value": "residential",           "confidence": "MEDIUM"},
    "urgency":            {"value": "normal",                "confidence": "MEDIUM"},
    "source_of_truth":    "email_primary",
    "gaps":               ["lot size not available"],
    "summary":            "..."
  }
}
```

---

## 5. Teams Integration

### Two separate APIs in use:

| Operation | API | Endpoint | Permission |
|-----------|-----|----------|-----------|
| Post invoice draft to chat | MS Graph v1.0 | `POST /chats/{chatId}/messages` | `Chat.ReadWrite.All` |
| Read approval replies | MS Graph v1.0 | `GET /chats/{chatId}/messages/{id}/replies` | `Chat.Read.All` |
| Post reply in thread | MS Graph v1.0 | `POST /chats/{chatId}/messages/{id}/replies` | `Chat.ReadWrite.All` |
| Post to approval channel | Logic App webhook | HTTP POST | webhook secret |
| Read channel approvals | MS Graph v1.0 | `GET /teams/{teamId}/channels/{channelId}/messages` | `ChannelMessage.Read.All` |

**Group chat ID (for invoice approvals):** `19:b88d010aa8254609937c512aded09e5f@thread.v2`

### Auth flow:
1. Client credentials grant (no user context) — `TEAMS_APP_ID` + `TEAMS_CLIENT_SECRET` → Bearer token
2. Token cached in memory, refreshed 60s before expiry
3. All Graph API calls use this token in `Authorization: Bearer` header

---

## 6. Database Schema (Sprint 11 additions)

### `processed_orders` (existing table — new columns added)

| Column | Type | Added By | Purpose |
|--------|------|----------|---------|
| `invoice_draft` | TEXT | migration 002 | JSON blob — current invoice draft |
| `data_sources` | TEXT | migration 002 | JSON blob — full order packet from A2 |
| `approval_message_id` | TEXT | migration 002 | Teams message ID where draft was posted |
| `modification_count` | INTEGER | migration 002 | How many modifications A4 has applied |
| `invoice_id` | TEXT | migration 002 | FTF invoice ID after A5 creates it |
| `client_name` | TEXT | migration 002 | Resolved client name |
| `property_address` | TEXT | migration 002 | Full property address |
| `data_collected_at` | TIMESTAMPTZ | migration 002 | When A2 completed |
| `draft_posted_at` | TIMESTAMPTZ | migration 002 | When A3 posted to Teams |
| `invoice_created_at` | TIMESTAMPTZ | migration 002 | When A5 created in FTF |

### `invoice_learnings` (new table — migration 002)

| Column | Type | Purpose |
|--------|------|---------|
| `id` | SERIAL PK | |
| `order_id` | TEXT | Which order triggered this learning |
| `original_draft` | TEXT | What AI originally proposed |
| `human_correction` | TEXT | What the human said (raw reply text) |
| `learned_rule` | TEXT | AI-generated summary of what to remember |
| `service_type` | TEXT | For filtered lookup |
| `county` | TEXT | For filtered lookup |
| `entered_by` | TEXT | Who made the correction (Robert, Ryan, Prateek) |
| `created_at` | TIMESTAMPTZ | |

---

## 7. Pricing Priority

A3 uses this lookup hierarchy when pricing a service:

```
1. pricing_examples table
   └─ Exact service + exact county → median of recent examples (entered by Robert/Ryan)
   └─ Exact service (any county)   → median of examples

2. invoice_learnings table
   └─ Service + county match → extract price from past corrections

3. Base rates (hardcoded from production data analysis, 18,497 orders)
   └─ Land Survey Only:         $450
   └─ Elevation Certificate:    $225
   └─ Land Survey + Elevation:  $400
   └─ Commercial (any):         $2,100
   └─ Topographic Survey:       $600
   └─ Default (unknown):        $450

4. B2B multiplier: × 1.3 applied on top of any tier
```

---

## 8. Environment Variables

### Required for invoice pipeline (all must be set in GitHub Secrets):

```
# FTF
FTF_API_KEY=
FTF_API_BASE_URL=https://stage.fieldtofinish.jobs/ftf-ai-api/v1
FTF_ORDER_URL=https://stage.fieldtofinish.jobs/admin/orders

# AI
ANTHROPIC_API_KEY=

# PostgreSQL
DB_HOST=
DB_PORT=5432
DB_NAME=ftf_agentic_ai
DB_USER=
DB_PASSWORD=

# MS Teams — Graph API (for channel + chat)
TEAMS_TENANT_ID=
TEAMS_APP_ID=
TEAMS_CLIENT_SECRET=
TEAMS_TEAM_ID=
TEAMS_CHANNEL_ID=
TEAMS_CHAT_ID=19:b88d010aa8254609937c512aded09e5f@thread.v2    # ← NEW
TEAMS_INCOMING_WEBHOOK_URL=                                     # Logic App (send to channel)

# Email inbox (read order context)
IMAP_HOST=outlook.office365.com                                 # ← NEW
IMAP_PORT=993                                                   # ← NEW
IMAP_USER=nesa@nexgenlogix.com                                  # ← NEW
IMAP_PASSWORD=                                                  # ← NEW

# Email sending (send invoice to client)
SMTP_HOST=                                                      # ← NEW
SMTP_PORT=587                                                   # ← NEW
SMTP_USER=nesa@nexgenlogix.com                                  # ← NEW
SMTP_PASSWORD=                                                  # ← NEW
SMTP_FROM=nesa@nexgenlogix.com                                  # ← NEW (overrides wrong default)

# Pipeline behaviour
MAX_INVOICE_MODIFICATIONS=5                                     # ← NEW
APPROVED_SENDERS=robert,ryan,prateek
```

---

## 9. Known Gaps (to build next)

| Gap | Description | Priority |
|-----|-------------|---------|
| Reply deduplication | A4 re-processes same replies every cycle | BLOCKER |
| Concurrent run guard | Two GitHub Actions runs can race on same order | HIGH |
| IMAP server-side search | A2 downloads ALL emails instead of searching | HIGH |
| Error Teams notification | Crashed agents post to Teams silently | HIGH |
| Order retry counter | Failed orders loop forever — need max 3 retries then escalate | HIGH |
| Flag clear verification | A5 doesn't confirm $ flag gone after invoice creation | MEDIUM |
| Teams message pagination | A2 only reads 200 messages — misses older context | MEDIUM |
| Graph API email search | Upgrade A2 from IMAP to MS Graph `/users/{email}/messages` | MEDIUM |
| Shadow mode | AI runs alongside humans, suggests but doesn't send | LOW (Sprint 12) |

---

## 10. Infrastructure

| Layer | Technology | Notes |
|-------|-----------|-------|
| Scheduling | GitHub Actions | Every 15 min — `invoice_pipeline.yml` |
| Runtime | Python 3.11 | ubuntu-latest runner |
| AI | Claude Sonnet 4.6 (primary), Claude Haiku 4.5 (fast classify) | Anthropic API |
| AI (local) | Hermes3 via Ollama | Low-cost classification — requires local machine running |
| State | PostgreSQL | `ftf_agentic_ai` database |
| Teams | MS Graph API v1.0 | Azure AD app, client credentials |
| FTF | REST API | Bearer token auth, 500 orders/page |
| Email (read) | IMAP SSL port 993 | `nesa@nexgenlogix.com` |
| Email (send) | SMTP TLS port 587 | `nesa@nexgenlogix.com` |
| Code | GitHub | `Nexgen-AI-Agents/FTF--Survey-Invoicing-Billing-Delivery-E2E-` |

---

## 11. Phase 2 — Not In Scope Yet

Everything below is built and waiting — infrastructure is live, just not triggered in prod.

| Loop | Agents | Trigger | Status |
|------|--------|---------|--------|
| AR Follow-Up | 10, 11 (scanner + escalation) | Daily cron | Staging — not prod |
| Monthly Statements | 15, 16, 17 (gen + review + send) | 1st of month | Staging — not prod |
| Win-back Email Agent | New (I-098) | Weekly | Not built yet |
| Upsell Campaigns | New (I-090) | Post-delivery | Not built yet |
| Website Chat Conversion | New (I-062) | Real-time | Not built yet |
