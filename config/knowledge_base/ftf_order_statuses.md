# FTF Order Status Hierarchy

> Confirmed by Prateek via FTF staging CRM — 2026-05-22.
> Use this file anywhere FTF order status logic is needed (monitor filter, classifier, AR loop, etc.)

---

## All Statuses

| Status | Purpose |
|--------|---------|
| **Quote** | Order requested but not yet accepted/activated — still in pricing/proposal stage |
| **Pending** | Order confirmed and active — waiting to be assigned to a field surveyor |
| **Needs FP** | Needs a Field Pack — property data/materials must be prepared before a surveyor can be dispatched |
| **Assigned** | Surveyor has been assigned but hasn't accepted or gone to the field yet |
| **In-Field** | Surveyor accepted the job and is actively on-site collecting survey data |
| **Drafting Queue** | Field work done — order is queued waiting for a drafter to pick it up |
| **Drafting** | A drafter is actively working on the survey drawings |
| **Checking** | Drafted survey is under QA review by a checker |
| **Complete** | Survey passed QA — ready to be invoiced and delivered to client |
| **Delivered** | Invoice sent and survey delivered to the title company/client |
| **Go Back** | QA failed or client requested correction — order sent back for rework |
| **On Hold** | Order paused — could be waiting on client, missing info, scheduling issue, etc. |
| **In Progress** | Generic in-motion state (appears unused currently — 0 orders) |
| **Set Corners** | Specific survey type requiring physical corner markers to be set on-site |
| **Set Up** | Order setup/configuration pending (also unused currently — 0 orders) |
| **Canceled** | Order was canceled before completion |

---

## Core Production Pipeline

```
Quote → Pending → Assigned → In-Field → Drafting Queue → Drafting → Checking → Complete → Delivered
```

---

## Agent-Specific Usage

### Agent 2 — Monitor (Sprint 1)
- **Only process orders with `status = "Quote"`**
- All other statuses = order is already in production or completed — no estimate needed
- Rationale: "Quote" is the only stage where an estimate has not yet been sent. Once accepted, order moves to "Pending" and is in the production pipeline.

### Agent 3 — Classifier (Sprint 2)
- Input orders will always be `status = "Quote"` (filtered by monitor)
- Classifier does not need to re-check FTF status

### Agent 10–14 — AR Follow-Up Loop (Sprint 7)
- Target orders with `status = "Delivered"` where invoice is unpaid past threshold
- `status = "Complete"` = not yet invoiced — not yet AR-eligible

### Agent 15–17 — Monthly Statements (Sprint 8)
- Target orders with `status = "Delivered"` within the billing month for B2B clients

---

## Notes

- `"In Progress"` and `"Set Up"` appear unused in staging (0 orders) — treat as edge cases if encountered
- `"Go Back"` can appear at any stage post-Checking — monitor should NOT re-pick these up as new orders
- `"On Hold"` orders remain in the pipeline — they will not re-trigger as new orders (covered by `order_exists()` deduplication)
