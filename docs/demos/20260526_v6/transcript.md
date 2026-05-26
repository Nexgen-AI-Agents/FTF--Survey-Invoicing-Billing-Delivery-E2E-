# FTF Agentic AI — Client Demo v6
**Total duration:** 4m 21s
**Date:** 2026-05-26  |  **Voice:** OpenAI TTS nova (0.85x)  |  **Sprint 0-9 · AR Data Live**

---

## Scene 1 — Introduction  [00:00 – 00:15]

> Welcome. Let me show you exactly what we built — 9 AI agents that automate your entire quoting process, connected to over 78,000 live invoices. We'll follow one real order, start to finish.

---

## Scene 2 — The Problem  [00:15 – 00:28]

> Before: your team had to manually check Field to Finish for new orders, look up the price, write the email, and send it. 50 new orders a week — hours of repetitive work every day.

---

## Scene 3 — Pipeline Overview  [00:28 – 00:46]

> The solution: 9 AI agents running around the clock. Detect, classify, price, approve if needed, write, review, send, report — and now: a real-time listener that eliminates the wait between every step. 8 complete sprints, 203 automated tests.

---

## Scene 4 — Meet the Order  [00:46 – 01:00]

> Let's follow John Martinez. He submits a Boundary Survey request at 9:14 AM. Half an acre, Hillsborough County. He's waiting for a quote. Before this system — he might wait until tomorrow.

---

## Scene 5 — Agent 2 — Monitor  [01:00 – 01:13]

> Agent 2 scans Field to Finish every 60 minutes. It finds John's order, confirms it's new, and logs it to the database. Status: pending. Nobody on your team did anything.

---

## Scene 6 — Classify & Price  [01:13 – 01:30]

> Agent 3 runs 14 checks in under 2 seconds. Standard service, Florida property, no competitor, no flood zone issues — all 14 checks pass. Agent 5 pulls the price from Field to Finish: 350 dollars.

---

## Scene 7 — Human Approval Gate  [01:30 – 01:47]

> For complex orders — like this ALTA Survey in Monroe County — Agent 4 sends Robert a Teams alert instantly. Robert reviews it, types approve, and the pipeline continues. Nothing sensitive goes out without a human sign-off.

---

## Scene 8 — Write, Review & Send  [01:47 – 02:15]

> Back to John. Agent 6 drafts a personalized estimate email with his name, property address, and the exact service requested. Agent 7 runs 4 accuracy checks: price match, client name, address verification, and change order clause. All 4 pass. Agent 8 delivers the quote to John's inbox. From order detected to email sent — under 2 minutes. No one on your team touched a thing.

---

## Scene 9 — Sprint 9 — Memory Loop  [02:15 – 02:44]

> Sprint 9 adds three things the pipeline was missing. A real-time database listener: the instant Agent 2 saves an order, a PostgreSQL trigger fires and the full pipeline runs immediately. A nightly memory log: every decision every agent made, written to a structured file. And a 7-day pattern analyzer that flags any agent falling below 90 percent accuracy. The system now watches itself.

---

## Scene 10 — AR Report Skill  [02:45 – 03:24]

> We also built a live accounts receivable skill. Every morning it logs into FTF Books, downloads the full unpaid invoice list — over 2,100 invoices in the Books module, 78,000 records accessible via the REST API — and builds a two-tab Excel report. Unpaid detail with aging buckets: 0 to 29 days, 30 to 59, 60 to 89, 90 to 364, and over 365. Plus a pivot summary sorted by total owed per company. The report runs on demand. No spreadsheet work. No manual login.

---

## Scene 11 — Sprint 10-12 Roadmap  [03:24 – 03:51]

> Here is what comes next. Sprint 7 automates AR follow-up reminders for overdue invoices. Sprint 8 generates monthly statements automatically. Both are ready to build the moment Jessica and Wyatt record their current process. Sprint 10 is the full staging test, followed by a limited launch, and then full production. The path is clear and every dependency is documented.

---

## Scene 12 — Summary  [03:52 – 04:21]

> To summarize what has been built. 9 AI agents handling your entire quoting pipeline. 203 automated tests keeping every component verified. The AR report skill delivering live receivables data every morning. Orders that used to take 5 hours now complete in under 2 minutes. Your process runs automatically, reports on itself, and scales with your volume. Thank you for your time.

---
