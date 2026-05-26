# FTF AR Report

Generates a formatted Accounts Receivable Excel report from the Field to Finish Books module.

## What it produces

Two-sheet Excel workbook named `Unpaid_AR_Report_MM.DD.YYYY.xlsx`:

- **Unpaid_{date}** — Full detail of every unpaid invoice with 12 columns, hyperlinked order numbers, currency formatting, auto-fitted columns, frozen header row
- **Summary_{date}** — Pivot by company vs aging bucket, sorted by Grand Total descending

## How to run it

```bash
python3 skills/ftf_ar_report/scripts/build_ar_report.py --output <outputs_dir>
```

The script will print the full path of the saved file when done. Provide that path to the user as a `computer://` link.

## Columns in Unpaid sheet

| Column | Notes |
|--------|-------|
| Company Name | Trimmed |
| Order | Hyperlink to https://fieldtofinish.jobs/order/?order={order} |
| File | File/case number |
| Name | Surveyor/POC name |
| Address | Property address |
| Date Ordered | YYYY-MM-DD |
| Date Delivered | YYYY-MM-DD or blank |
| Days Since Delivery | Integer, calculated from today |
| Group | Aging bucket: 0-29 / 30-59 / 60-89 / 90-364 / Over 365 |
| Amount | Currency #,##0.00 |
| Paid | Currency #,##0.00 |
| Owed | Currency #,##0.00 |

## Aging bucket logic

| Days Since Delivery | Group |
|--------------------|-------|
| 0–29 | 0-29 |
| 30–59 | 30-59 |
| 60–89 | 60-89 |
| 90–364 | 90-364 |
| 365+ | Over 365 |

If no delivery date, days = 0, group = 0-29.

## Credentials

Set in `.env` (never committed):

```
FTF_BOOKS_BASE_URL=https://stage.fieldtofinish.jobs
FTF_BOOKS_USER=<your-username>
FTF_BOOKS_PASSWORD=<your-password>
```

- Login URL: `POST {FTF_BOOKS_BASE_URL}/admin/login`
- Header required: `X-Requested-With: XMLHttpRequest`
- Download URL: `GET {FTF_BOOKS_BASE_URL}/books/get_data_excel?show_all=1`

## Error handling

If login fails or the download returns non-xlsx content, print a clear error and stop.
Do not silently produce an empty file.

## Unblocks

- **Sprint 7** — AR Follow-Up Loop: `agent_10_ar_scanner.py` can use the API `/invoices?status=unpaid` (78k+ unpaid invoices available on staging)
- **Sprint 8** — Monthly Statements: `agent_15_statement_generator.py` can call `build_ar_report.py` and attach the xlsx to Teams + email delivery
