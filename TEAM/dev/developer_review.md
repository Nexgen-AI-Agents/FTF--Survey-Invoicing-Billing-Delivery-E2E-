# Developer Review Log — FTF Agentic AI OS

> **INSTRUCTION FOR ALL DEVELOPERS:** Read this file before starting any task.
> Append a new entry any time: a bug is found and fixed, a coding pattern is confirmed, or a non-obvious decision is made.
> Format: `## [YYYY-MM-DD] — Short title` then bullet points.
> All three developers (Manager, Senior, Junior) read and contribute to this file.

---

## [2026-06-05] — Python `or` doesn't protect against AI-returned sentinel strings

**File:** `code/sprint_11_invoice_pipeline/agents/agent_a2_data_collector.py`

- **Bug:** Code used `str(packet.get("client_name", {}).get("value") or client_name)` to save AI-extracted data with a DB fallback. This pattern is broken when the AI returns `"Unknown"` — Python's `or` only triggers the right side when the left side is **falsy**, and `"Unknown"` is truthy.
- **Impact:** 3+ orders had `client_name = "Unknown"` and `property_address = "Unknown"` in pipeline state even though MySQL had valid values (confirmed via DB query).
- **Fix:** Module-level `_resolve_field(extracted_val, fallback)` helper + `_UNKNOWN_SENTINELS` frozenset. Guards against: `"unknown"`, `"n/a"`, `"none"`, `"not available"`, `"not found"`, `""`.
- **Rule for all devs:** Never use bare `or` to fall back from AI-extracted values. AI models return non-empty sentinel strings when data is missing. Always use sentinel-aware resolution.

```python
# WRONG
value = str(ai_result.get("field", {}).get("value") or db_fallback)

# CORRECT
value = _resolve_field(ai_result.get("field", {}).get("value"), db_fallback)
```

---

## [2026-06-05] — Excel state schema gap silently broke county lookup

- **Bug:** A2 read county from `db_row.get("county", "")` but Excel state has no `county` column — A1 never saved it. Result: silent empty string propagated to appraiser lookup → "No county provided" error.
- **Rule:** When adding a new field dependency in A2 (or any agent reading from Excel), verify the field actually exists in the Excel schema (`excel_db.py` column list). If not, add a direct MySQL fallback via `mysql_get_order_details()`.
- **Fix:** `mysql_get_order_details(order_id)` is now called as fallback when `_db_county` is empty.

---

## [2026-06-05] — Skills library added — use these before debugging manually

Five scripts in `skills/` folder that every dev should know:

| Script | When to run |
|--------|-------------|
| `python skills/pipeline-status/run.py` | Before/after any fix — get status counts |
| `python skills/verify-a2-output/run.py` | After any A2 fix — confirm no sentinels |
| `python skills/check-dollar-sign-orders/run.py` | Find orders with `$` but no amount |
| `python skills/requeue-orders/run.py --orders X --target-status invoice_needed --clear invoice_draft,data_sources` | Re-queue orders for reprocessing |
| `python skills/full-pipeline-retest/run.py --orders X` | End-to-end retest after a fix |
