# Issue Tracker — FTF Agentic AI OS

## Status Lifecycle

```
OPEN → IN DEV → DEV COMPLETE → QA JUNIOR → QA SENIOR → QA MANAGER → RELEASED → CLOSED
                                      ↑____________________________|
                                      (QA FAIL at any level → back to IN DEV)
```

## Severity Definitions

| Severity | Meaning |
|----------|---------|
| **BLOCKER** | Cannot proceed to next sprint. Stops all work on this sprint now. |
| **CRITICAL** | Must fix before release. Does not block other sprint work. |
| **MAJOR** | Significant regression or incorrect behavior. Should fix in current sprint. |
| **MINOR** | Cosmetic or low-impact. Tracked but not sprint-blocking. |

---

## Open Issues

| ID | Sprint | Severity | Title | Assigned | Status | Opened | Notes |
|----|--------|----------|-------|----------|--------|--------|-------|
| I-003 | Sprint 2 | CRITICAL | Exact FTF names for Construction + Permitting surveys unknown | dev_manager | OPEN | 2026-05-21 | Robert/Mark must provide before Sprint 2 (Classifier). 22 of 24 services confirmed. These 2 cannot be classified correctly without exact names. |
| I-005 | Sprint 2 | MAJOR | Wetland Delineation — does NexGen perform this service? | dev_manager | OPEN | 2026-05-21 | `service_names.json`: `"flag": "pending_confirmation"`. Robert/Mark to confirm if this service should be in the 24-service list or removed. |
| I-006 | Sprint 7 | CRITICAL | Jessica recording (Recording 10) not yet conducted | dev_manager | OPEN | 2026-05-21 | Blocks Sprint 7 AR loop. Need: exact 5-tier reminder schedule, 90-day escalation confirmation, client exclusion list. Jessica AI agent STUB until enriched. |
| I-007 | Sprint 8 | CRITICAL | Wyatt recording (Recording 11) not yet conducted | dev_manager | OPEN | 2026-05-21 | Blocks Sprint 8 monthly statements. Need: statement format confirmation, B2B delivery method confirmation. Wyatt AI agent STUB until enriched. |
| I-008 | Sprint 6 | MAJOR | Change order clause not reviewed by Ryan before go-live | dev_manager | OPEN | 2026-05-21 | `config/knowledge_base/change_order_clause.txt` must be drafted and sent to Ryan for review before Sprint 6 milestone. Confirmed: in-house draft, not blocked for build. |
| I-013 | Sprint 11 | MAJOR | FTF API returns 207,622 orders but CRM shows 275,693 — 68,071 orders missing from API | dev_manager | OPEN | 2026-05-22 | Probed all params (archived, deleted, all, include_archived) — total fixed at 207,622. Likely API key scope issue. Also: order 1000276072 API=Quote, CRM=Checking — status field accuracy unconfirmed. Code is correct; this is a pre-production concern only. FTF developer to answer before Sprint 11 go-live: (1) Why are 68,071 orders missing? (2) Is the API key scoped to a subset? (3) Does `?status=Quote` reliably reflect CRM status? Does NOT block Sprint 2 or any build sprint. |
| I-017 | Sprint 2 | MAJOR | Monitor stores only order_id at detection time — Classifier must call get_order() per order, API call volume impact unknown | dev_manager | OPEN | 2026-05-22 | Raised by BA review. processed_orders table has no property_address, customer_id, created_at columns. Sprint 2 Classifier must call get_order(order_id) for each pending order to retrieve data needed for classification. With 500+ orders per run, this is 500+ sequential API calls. Confirm FTF API rate limit applies to bulk GET /orders only (not individual GETs) before Sprint 2 design is finalized. |
| I-018 | Sprint 6 | MINOR | PII masking in logger.py covers email addresses only — phone numbers, property addresses, customer names logged in plain text | dev_manager | OPEN | 2026-05-22 | Raised by Dev Manager + BA review. logger.py _mask_pii() regex matches email format only. Property addresses and customer names will flow through Sprint 2+. Must be resolved before Sprint 6 (Sender) when real customer data flows through estimate emails. Not urgent for Sprint 2. |
| I-019 | Sprint 10 | MINOR | No prompt caching in claude_client.py — cost risk at scale with 7000+ Quote orders | dev_manager | OPEN | 2026-05-22 | Raised by BA review. claude_client.py does not implement cache_control headers. At staging scale (Sprint 10 cost benchmark), every reasoning agent call is a fresh context. Recommend adding cache_control to system prompts before Sprint 10. Non-blocking until then. |
| I-023 | Sprint 3 | MINOR | Add CLI manual trigger for Agent 2 Monitor — build now | dev_manager | OPEN | 2026-05-22 | Confirmed 2026-05-25 by Prateek: build the manual trigger now. 60-min scheduled polling is acceptable for production. Add a CLI entrypoint (e.g., `python -m agents.agent_02_monitor --run-now`) that calls `agent_02_monitor.run()` on demand without waiting for the next scheduled poll. Useful for urgent orders and ops team manual checks. |
| I-025 | Sprint 3 | MAJOR | Approval inbound mechanism — Teams bot must read Robert/Mark chat replies | dev_manager | OPEN | 2026-05-22 | Mechanism confirmed 2026-05-25 by Prateek: Robert or Mark types "approve" or "reject" in the Teams chat thread, and a bot reads the reply and updates the order status in the DB. Technical requirement: build a Teams bot (webhook listener or polling bot) that reads chat replies on the flagged-order thread and maps them to status="approved" or status="rejected" in processed_orders. Timeout SLA and escalation path still TBD — to be defined before Sprint 3 bot implementation. |
| I-026 | Sprint 4 | MAJOR | Change order clause — drafted, awaiting Ryan review before Sprint 4 go-live | dev_manager | OPEN | 2026-05-22 | Clause drafted 2026-05-25 at `config/knowledge_base/change_order_clause.txt`. Covers: what constitutes a change order, how to request one, pricing/payment terms, limitation of liability. Ryan must read and approve (or redline) before Sprint 4 code is finalized — clause text is referenced in Sprint 6 email templates; late changes would require template rework. Status: OPEN until Ryan confirms wording. |
| I-028 | Sprint 7 | MINOR | Agent 5 Reviewer must log both pre-correction and post-correction estimate for Sprint 7 demo | dev_manager | OPEN | 2026-05-22 | Confirmed 2026-05-25 by Prateek. agent_05_reviewer.py must log: (1) the initial draft estimate text before the self-correction loop, and (2) the final corrected estimate text after all review passes complete. Sprint 7 demo will show these side-by-side so stakeholders can see the AI improving its own output. Design logging into agent_05_reviewer.py at Sprint 7 build time. |
| I-032 | Sprint 8 | MAJOR | Recording 11 prerequisites unmet — draft template, B2B client list, and Excel vs PDF spec needed before recording | dev_manager | OPEN | 2026-05-22 | Raised by Wyatt AI Phase 1 demo. Recording 11 (Wyatt, monthly statements) has 3 prerequisites that must exist before the recording can happen: (1) a draft statement template for Wyatt to react to, (2) the confirmed B2B client list, (3) clarification of whether B2B clients receive Excel vs PDF (different content structure). Without these, Recording 11 will be unproductive. Action: prepare all 3 artifacts before scheduling Recording 11. |

---

## Closed Issues

| ID | Sprint | Severity | Title | Resolved By | Closed | Resolution |
|----|--------|----------|-------|-------------|--------|------------|
| I-001 | Sprint 2 | CRITICAL | Competitor names + domains list missing — Agent 4 flag logic incomplete | competitor_analyst | 2026-05-25 | Bootstrapped from Florida market web research. 25 competitor names + 16 domains added to `flag_triggers.py`. Source: `TEAM/research/competitive_analysis.md`. Robert/Mark to validate list before Sprint 3. |
| I-002 | Sprint 2 | CRITICAL | Never-auto-quote service list missing — Agent 4 flag trigger #2 incomplete | competitor_analyst | 2026-05-25 | Bootstrapped from web research. `NEVER_AUTO_QUOTE` populated: Specific Purpose Survey, Lot Split, Wetland Delineation. Robert/Mark to validate before Sprint 3. |
| I-009 | Sprint 0 | CRITICAL | `db.get_pending_order()` used in sprint plan to check if order exists — function takes no args | dev_manager | 2026-05-21 | Added `order_exists(order_id: str) -> bool` to `core/db.py`. Sprint 1 agent uses this instead. |
| I-010 | Sprint 0 | MINOR | `test_get_pricing_raises_pricing_error_on_failure` called `get_pricing()` without required `service` arg | dev_manager | 2026-05-21 | Fixed test to call `get_pricing("Boundary Survey")`. |
| I-011 | Sprint 0 | MINOR | `state.py` uses deprecated `datetime.datetime.utcnow()` — DeprecationWarning on Python 3.14 | dev_manager | 2026-05-21 | Replaced all 4 calls with `datetime.datetime.now(datetime.UTC)`. |
| I-012 | Sprint 1 | MAJOR | Monitor saved ALL FTF orders regardless of status — Delivered/Complete/Cancelled orders incorrectly queued | dev_manager | 2026-05-22 | Added FTF status filter: only `status="Quote"` orders are processed. Confirmed via FTF staging CRM — order 1000275451 was Delivered but appeared in queue. Added UT-01-07 to cover this case. 8/8 tests pass. |
| I-020 | Sprint 2 | MAJOR | ftf_client.py pagination silently returns empty list if API returns total=0 on first call | dev_manager | 2026-05-22 | Added `logger.warning` when `offset == 0 and total == 0` in `get_orders()`. 51/51 tests pass. |
| I-021 | Sprint 2 | MAJOR | logger.py dict-style record.args converted to string before masking — breaks dict-format log calls with TypeError | dev_manager | 2026-05-22 | Added `isinstance(record.args, dict)` branch in `_PIIFilter.filter()` — masks dict values individually: `{k: _mask_pii(str(v)) for k, v in record.args.items()}`. 51/51 tests pass. |
| I-022 | Sprint 2 | MINOR | SERVICE_STATE = "FL" defined in both flag_triggers.py and settings.py — duplicate constant, one is dead code | dev_manager | 2026-05-22 | Removed `SERVICE_STATE = "FL"` from `flag_triggers.py`. `settings.py` is the authoritative home. 51/51 tests pass. |
| I-014 | Sprint 2 | BLOCKER | Geocoding capability missing — no way to convert property_address to lat/lng for FEMA flood zone check | dev_manager | 2026-05-25 | RESOLVED — API probe confirmed `GET /orders/{id}` always returns `property_lat` and `property_lng`. No geocoding service needed. Additionally, `flood_zone` is pre-populated by FTF for most orders — FEMA API call only needed when `flood_zone` is null. `core/geocoding_client.py` will NOT be built. See `config/knowledge_base/ftf_api_schemas.md`. |
| I-015 | Sprint 2 | CRITICAL | GET /orders/{id} individual order response schema unknown — may be only path to actual service_type | dev_manager | 2026-05-25 | RESOLVED — Full schema confirmed via staging probe 2026-05-25. 26 fields including `service_type` (actual name or "Quote"), `customer_type`, `customer_email`, `property_lat`, `property_lng`, `flood_zone`, `elevation_cert`, `special_pricing`. Schema documented in `config/knowledge_base/ftf_api_schemas.md`. New finding: service_type="Quote" for unclassified orders → logged as I-033. |
| I-016 | Sprint 2 | CRITICAL | GET /customers/{id} response schema unknown — customer type (B2B/individual) and email field names unconfirmed | dev_manager | 2026-05-25 | RESOLVED — Full schema confirmed via staging probe 2026-05-25. Key fields: `customer_type` ("individual"/"b2b"), `email`, `pricing_type` (0=individual, 1=b2b unconfirmed), `custom_rate`, `special_pricing`. NOTE: `customer_type` and email are already in the order response — separate customer call only needed for `custom_rate` / `pricing_type`. Schema documented in `config/knowledge_base/ftf_api_schemas.md`. |
| I-029 | Sprint 2 | MAJOR | Audit log (agent_decision_log) has no append-only access control — agents could overwrite prior records | dev_manager | 2026-05-25 | Application-layer dedup guard added to `log_decision()` in `core/db.py`: SELECT checks for identical (agent_name, order_id, decision) within 30s window before INSERT. Prevents overwrite without requiring DB-level trigger. `test_log_decision_inserts_row` updated to expect SELECT+INSERT (2 cursor.execute calls). 119/119 tests pass. |
| I-034 | Sprint 3 | MAJOR | Monroe County flag trigger missing — Florida Keys orders need human review (non-standard pricing) | dev_manager | 2026-05-25 | Added Monroe County hard flag to `agent_03_classifier.py`: if `property_county` contains "monroe" (case-insensitive), order is flagged with reason "Monroe County (Florida Keys) — non-standard pricing, human review required". Test UT-02-18 added (3 sub-cases). 119/119 tests pass. |
| I-035 | Sprint 2 | MAJOR | VE coastal flood zone not flagged — elevation cert required but classifier missing this trigger | dev_manager | 2026-05-25 | VE zone flag added to `agent_03_classifier.py`: if `flood_zone` starts with "VE", order is flagged — VE zones require elevation certificate and specialist review. Test UT-02-12 added. 119/119 tests pass. |
| I-036 | Sprint 2 | MAJOR | Missing property_county not flagged — classifier cannot apply county-specific pricing rules | dev_manager | 2026-05-25 | Missing county flag added to `agent_03_classifier.py`: if `property_county` is empty/None, order is flagged — county is required for Monroe County check and future county-specific pricing. Test UT-02-13 added. 119/119 tests pass. |
| I-037 | Sprint 2 | MAJOR | property_lat outside Florida bounds not flagged — out-of-state lat/lng goes undetected when state field is blank | dev_manager | 2026-05-25 | FL bounds lat check added to `agent_03_classifier.py`: if `property_state == "FL"` but `property_lat` is outside Florida's lat range (24.4–31.0), flag as "property_lat outside Florida bounds — possible data entry error". Trigger 9 (out-of-state via property_state) is separate and coexists. Test UT-02-14 + UT-02-17 updated. 119/119 tests pass. |
| I-004 | Sprint 2 | MAJOR | B-II Title Review flag status unconfirmed | dev_manager | 2026-05-25 | Confirmed by Prateek: B-II Title Review is auto-quoteable — no human review required. Removed from `NEVER_AUTO_QUOTE` in `flag_triggers.py`. |
| I-024 | Sprint 6 | MAJOR | Resend behavior for failed estimate emails undefined | dev_manager | 2026-05-25 | Confirmed by Prateek: (1) Emails may only be sent between 8AM–6PM EST — no sends outside this window. (2) On send failure, retry immediately (no delay reset). (3) Maximum 3 retry attempts before the send is marked failed. Sprint 6 Sender agent to implement this logic. |
| I-027 | Sprint 2 | MAJOR | Pricing sync method undefined | dev_manager | 2026-05-25 | Confirmed by Prateek: pricing.json is manually maintained — when FTF changes service rates, Prateek or ops team updates the file. FTF API-driven pricing sync is planned for a future sprint but not part of current scope. No code change needed now. |
| I-030 | Sprint 7 | CRITICAL | 90-day AR escalation behavior ambiguous — auto-send to client or flag Jessica? | dev_manager | 2026-05-25 | Confirmed by Prateek: NO auto-email to clients. At 60 days overdue: alert Jessica only. At 90 days overdue: alert Jessica + all stakeholders (Ryan, Mark, Robert, Wyatt). All escalations are internal alerts — a human must decide whether to contact the client directly. Sprint 7 AR agent to implement this two-tier alert schedule. |
| I-031 | Sprint 8 | MAJOR | No manual statement trigger defined — mid-month statement requests unhandled | dev_manager | 2026-05-25 | Confirmed by Prateek: mid-month statement requests are handled manually for now. System only auto-generates statements on the 1st of the month. No on-demand CLI trigger required at this stage. |
| I-033 | Sprint 2 | MAJOR | service_type="Quote" fallback strategy undefined | dev_manager | 2026-05-25 | Confirmed by Prateek: orders where service_type="Quote" (FTF staff have not yet classified them) are held as status="unknown" and flagged for Robert/Mark review. Classifier must not attempt to infer or auto-quote these orders. Flag reason: "service_type=Quote — unclassified by FTF staff, held for manual review." |
| I-038 | Sprint 3 | MAJOR | Competitor list false-positive-risk entries + unconfirmed domains | dev_manager | 2026-05-25 | Confirmed by Prateek: "Florida Land Surveying" is a real competitor (floridalandsurveying.com). "Atlantic Coast Surveying" is a real competitor (acsiweb.net = Atlantic Coast Surveying Inc). Both names and domains confirmed and kept in `flag_triggers.py`. Comments updated — false-positive-risk flags removed. |

---

## Issue ID Format

`I-NNN` — sequential. Example: `I-001`, `I-002`, `I-003`.

## How to Log a New Issue

Add a row to **Open Issues** with:
- **ID**: next sequential number
- **Sprint**: which sprint's code (e.g., Sprint 0)
- **Severity**: BLOCKER / CRITICAL / MAJOR / MINOR
- **Title**: one-line description of the problem
- **Assigned**: `junior_dev`, `senior_dev`, or `dev_manager`
- **Status**: `OPEN`
- **Opened**: YYYY-MM-DD
- **Notes**: exact input that caused it + what happened + what was expected

## How to Close an Issue

Move the row to **Closed Issues** and fill in Resolved By, Closed date, and Resolution.
