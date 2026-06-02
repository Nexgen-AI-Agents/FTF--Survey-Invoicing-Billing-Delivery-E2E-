# FTF Sprint 11 — Agent Data Contracts

Defines what each agent reads from and writes to the Excel state store (`data/invoice_pipeline_state.xlsx`). All agents access state exclusively through `code/shared/core/excel_db.py`.

**Last Updated:** 2026-06-02

---

## Status Flow

```
(new MySQL order)
      |
      v
  invoice_needed        <- A1 writes
      |
      v
  data_collected        <- A2 writes
      |
      v
  invoice_draft_posted  <- A3 writes
      |
      v
  approved / rejected / on_hold  <- A4 writes
      |
      v (approved only)
  invoice_finalized     <- A5 writes
      |
      v
  invoice_sent          <- A6 writes
```

---

## Agent Contracts Table

| Agent | Input Status | Output Status | Key Fields Read | Key Fields Written |
|-------|-------------|--------------|----------------|-------------------|
| A0 — Orchestrator | any | (none directly) | Reads all rows to determine which agents to invoke; passes row data to A1–A6 | Writes nothing directly — delegates all writes to child agents |
| A1 — Order Detector | (none — queries MySQL) | `invoice_needed` | MySQL `nexgen_ftf_db`: `ng_orders` (order_id, client, type, completion date) | `order_id`, `status = invoice_needed`, `created_at` |
| A2 — Data Collector | `invoice_needed` | `data_collected` | `order_id` from Excel row | `data_sources` blob (dict containing: FTF API order detail, IMAP email thread, county URL lookup, aerial imagery metadata), `status = data_collected` |
| A3 — Invoice Drafter | `data_collected` | `invoice_draft_posted` | `data_sources` blob | `services` (list of line items), `total_amount` (float), `reasoning` (Claude explanation string), `teams_message_id` (Teams card message ID for reply matching), `status = invoice_draft_posted` |
| A4 — Approval Monitor | `invoice_draft_posted` | `approved` / `rejected` / `on_hold` | `teams_message_id` (to match Teams replies), `order_id` | `status` (one of: `approved`, `rejected`, `on_hold`), `decision_by` (Teams sender), `decision_at` (timestamp) |
| A5 — Invoice Finalizer | `approved` | `invoice_finalized` | `services`, `total_amount`, `order_id` | `ftf_invoice_id` (FTF Books invoice ID), `invoice_url` (direct link to invoice in FTF), `status = invoice_finalized` |
| A6 — Invoice Sender | `invoice_finalized` | `invoice_sent` | `ftf_invoice_id`, `invoice_url`, `order_id` | `sent_at` (ISO timestamp), `status = invoice_sent` |

---

## Field Name Contract

All invoice draft dicts (written by A3, read by A5) use these exact field names:

| Field | Correct Name | Wrong Names (do not use) |
|-------|-------------|--------------------------|
| List of invoice line items | `services` | `line_items`, `items`, `invoice_lines` |
| Total invoice amount (float) | `total_amount` | `invoice_amount`, `total`, `amount` |

This contract was formalized and enforced in commit `537754c` after A5 crashed reading `line_items` from an A3-written row that used `services`. All agents must use these names.

---

## data_sources Blob Structure

A2 writes a JSON-serializable dict to the `data_sources` column. Expected keys:

```python
{
    "ftf_order": { ... },          # Full FTF API order response
    "email_thread": [ ... ],       # List of IMAP email dicts (subject, body, date)
    "county_url": "https://...",   # County lookup URL (may be None)
    "aerial": {                    # Aerial imagery metadata (may be None)
        "provider": "...",
        "image_url": "...",
        "acreage": float
    }
}
```

A3 reads this blob in full. Missing keys (`county_url = None`, `aerial = None`) are acceptable — A3 gracefully degrades.

---

## Excel Column Reference

The following columns exist in `data/invoice_pipeline_state.xlsx`. Agents must not rename or reorder these.

| Column | Type | Written By | Notes |
|--------|------|-----------|-------|
| `order_id` | str | A1 | FTF order ID (primary key) |
| `status` | str | A1–A6 | Current pipeline status |
| `created_at` | datetime | A1 | Row creation timestamp |
| `data_sources` | str (JSON) | A2 | Serialized dict |
| `services` | str (JSON) | A3 | List of line item dicts |
| `total_amount` | float | A3 | Invoice total |
| `reasoning` | str | A3 | Claude's pricing rationale |
| `teams_message_id` | str | A3 | Teams card message ID |
| `decision_by` | str | A4 | Approver display name |
| `decision_at` | datetime | A4 | Approval/rejection timestamp |
| `ftf_invoice_id` | str | A5 | FTF Books invoice ID |
| `invoice_url` | str | A5 | FTF invoice direct URL |
| `sent_at` | datetime | A6 | Invoice send timestamp |

---

## Related

- [Architecture Index](README.md)
- [Invoice Pipeline Workflow](workflows/invoice_pipeline.md)
- `code/shared/core/excel_db.py` — state store implementation
- `data/invoice_pipeline_state.xlsx` — live state file
