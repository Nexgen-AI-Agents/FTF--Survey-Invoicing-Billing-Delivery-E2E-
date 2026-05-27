# Sprint 8 — Test Cases: Agents 15–17 Monthly Statement Loop

> Written by Senior QA before dev starts. All cases must pass before Sprint 8 is marked ✅ Complete.
> Reference: `sprints/sprint_08_monthly_statements.md`

---

## Unit Tests (`code/sprint_08_monthly_statements/tests/test_statement_generator.py` + `test_statement_reviewer.py` + `test_statement_sender.py`)

| ID | Scenario | Input | Expected Output | Pass? |
|----|----------|-------|-----------------|-------|
| UT-08-01 | `_order_row` unpaid — includes balance due | Unpaid B2B order, `amount=$500`, no payment | Row dict has `balance_due=500` | ✅ |
| UT-08-02 | `_order_row` paid — shows $0.00 balance | Paid B2B order, `amount=$500`, `paid=True` | Row dict has `balance_due=0.00` | ✅ |
| UT-08-03 | `_build_excel` creates .xlsx file | List of 3 B2B orders | `.xlsx` file created at `STATEMENT_OUTPUT_DIR/client_YYYY-MM.xlsx` | ✅ |
| UT-08-04 | Excel has "Unpaid Detail" + "Summary" sheets | Generated Excel file | Workbook has exactly 2 sheets: `"Unpaid Detail"` and `"Summary"` | ✅ |
| UT-08-05 | Detail tab row count matches order list | 5 orders passed | "Unpaid Detail" sheet has 5 data rows + 1 header row | ✅ |
| UT-08-06 | Summary tab totals reflect order amounts | 3 orders totaling $1,350 | Summary tab shows total `$1,350` | ✅ |
| UT-08-07 | `_build_pdf` creates .pdf file | Same 3 B2B orders | `.pdf` file created at `STATEMENT_OUTPUT_DIR/client_YYYY-MM.pdf` | ✅ |
| UT-08-08 | `_group_by_client` groups by billing email | Orders from 3 different billing emails | Returns dict with 3 keys (one per billing email) | ✅ |
| UT-08-09 | `_group_by_client` skips blank emails | 1 order with blank `billing_email` | That order excluded from grouping | ✅ |
| UT-08-10 | Agent 15 run generates 1 statement per client | 3 B2B clients with orders | 3 Excel + 3 PDF files created; 3 rows upserted to `monthly_statements` | ✅ |
| UT-08-11 | Reviewer validates correct statement → pass | Excel + PDF both present, row count matches | `monthly_statements.status = "reviewed"` | ✅ |
| UT-08-12 | Reviewer detects row count mismatch → fail | Excel has 3 rows but DB count says 4 | `monthly_statements.status = "failed"`; alert logged | ✅ |
| UT-08-13 | Reviewer handles missing Excel gracefully | Excel file not found at expected path | Returns failure status; no crash | ✅ |
| UT-08-14 | Reviewer marks valid statement `"reviewed"` | All validations pass | `update_statement_status(status="reviewed")` called | ✅ |
| UT-08-15 | Reviewer marks failed when PDF missing | PDF file not found | `update_statement_status(status="failed")` called | ✅ |
| UT-08-16 | Sender skips email if `SMTP_HOST` not set | `SMTP_HOST=None` | No SMTP connection attempted; logged as skipped | ✅ |
| UT-08-17 | Sender skips Teams notification if webhook not set | `TEAMS_WEBHOOK_URL=None` | No Teams POST; no crash | ✅ |
| UT-08-18 | Sender marks statement `"sent"` on success | SMTP send succeeds | `monthly_statements.status = "sent"` | ✅ |
| UT-08-19 | Sender marks `"failed"` on exception | SMTP raises `SMTPException` | `monthly_statements.status = "failed"` | ✅ |

---

## Integration Tests (Staging — Sprint 10)

| ID | Scenario | How to Run | Expected Result | Pass? |
|----|----------|-----------|-----------------|-------|
| IT-08-01 | Statement generated for 2 B2B clients on staging | Set test date to 1st of month; run `agent_15_statement_generator.py` with staging B2B orders | 2 Excel + 2 PDF files created in `STATEMENT_OUTPUT_DIR` | ✅ |
| IT-08-02 | Statement reviewer passes valid statement | Run `agent_16_statement_reviewer.py` after generator | Both statements advance to `status="reviewed"` | ✅ |
| IT-08-03 | Statement emailed to billing contact on staging | Run `agent_17_statement_sender.py` with staging SMTP | Email with Excel + PDF attachments arrives at test billing address | ✅ |
| IT-08-04 | Teams notification sent to Ryan, Wyatt, Jessica | Successful send | Teams channel receives notification listing client + amounts | ✅ |
| IT-08-05 | Wyatt confirms statement format on staging | Generate staging statement for Wyatt review | Wyatt approves Excel + PDF format and delivery method | ✅ |

---

## Edge Cases

| ID | Scenario | Expected Behavior | Pass? |
|----|----------|-------------------|-------|
| EC-08-01 | B2B client has 0 orders for the month | `get_b2b_orders_for_month()` returns empty list for that client | No statement generated for that client — no empty Excel/PDF | ✅ |
| EC-08-02 | Statement loop triggered on day other than 1st | Run on 2026-05-15 (not 1st) | No statements generated; returns early with logged reason | ✅ |
| EC-08-03 | Logger PII filter with integer `%d` format args | Log call like `logger.info("Count: %d", 5)` | Non-string args pass through unchanged — no `TypeError` | ✅ |
| EC-08-04 | Client billing email changes mid-month | Email changes between statement date and send date | Statement uses billing email from the time of generation; no re-grouping | ✅ |
| EC-08-05 | `get_b2b_orders_for_month()` returns all orders — filters client-side | FTF API does not support month/customer_type params | Client-side filter applied correctly; only prior month's B2B orders included | ✅ |
| EC-08-06 | SMTP send partially fails (1 of 3 clients) | SMTP raises exception for 1 client | That client marked `"failed"`; other 2 marked `"sent"` — no all-or-nothing | ✅ |

---

## Acceptance Criteria (All must be green to close Sprint 8)

- [ ] UT-08-01 through UT-08-19 all pass
- [ ] Excel has exactly 2 tabs: "Unpaid Detail" + "Summary"
- [ ] Excel columns: Order #, Service Type, Date of Service, Invoice Amount, Payment Status, Balance Due
- [ ] PDF summary generated alongside Excel for every statement
- [ ] Statement loop triggers on 1st of calendar month only
- [ ] `_group_by_client` correctly separates orders by billing email
- [ ] Blank billing emails skipped — no blank-email statement
- [ ] SMTP and Teams notifications both optional (skip gracefully if not configured)
- [ ] Logger PII filter does not break integer format strings
- [ ] Wyatt (Oversight) confirms statement format on staging
- [ ] Prateek (CTO) sign-off on all 19 tests

---

## Notes

- Integration tests (IT-*) run during Sprint 10 (full staging). Unit tests (UT-*) run during Sprint 8.
- Statement content is deterministic data formatting — no LLM needed for this sprint.
- `statement_generator.txt` prompt not needed; `reporter.txt` pattern from Sprint 6 not reused here.
- Logger fix: `_safe_mask()` only applies PII masking to string values; non-strings pass through unchanged.
- `update_statement_status` called with keyword args — tests assert against `call_args.kwargs["status"]`.
- Sprint 8 completed 2026-05-27 — 19/19 tests pass; full suite 239/239.
