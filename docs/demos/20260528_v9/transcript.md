# FTF Agentic AI — Client Demo v9
**Total duration:** 5m 56s
**Date:** 2026-05-28  |  **Voice:** OpenAI TTS nova (0.85x)  |  **Sprint 0-9 · 24/7 Auto-Poll**

---

## Scene 1 — Introduction  [00:00 – 00:15]

> Welcome. Let me show you exactly what we built — 9 AI agents that automate your entire quoting process, connected to over 78,000 live invoices. We'll follow one real order, start to finish.

---

## Scene 2 — The Problem  [00:15 – 00:28]

> Before: your team had to manually check Field to Finish for new orders, look up the price, write the email, and send it. Many new orders every week — hours of repetitive work every single day.

---

## Scene 3 — Pipeline Overview  [00:29 – 00:48]

> The solution: 9 AI agents running around the clock. Detect, classify, price, approve if needed, write, review, send, report — with a smart Teams approval channel and 24/7 automated monitoring via GitHub Actions. 9 complete sprints, 203 automated tests.

---

## Scene 4 — Meet the Order  [00:48 – 01:03]

> Let's follow John Martinez. He submits a Boundary Survey request at 9 14 AM. Half an acre, Hillsborough County. He's waiting for a quote. Before this system — he might wait until tomorrow.

---

## Scene 5 — Agent 2 — Monitor  [01:03 – 01:15]

> Agent 2 scans Field to Finish every 60 minutes. It finds John's order, confirms it's new, and logs it to the database. Status: pending. Nobody on your team did anything.

---

## Scene 6 — Classify & Price  [01:16 – 01:32]

> Agent 3 runs 14 checks in under 2 seconds. Standard service, Florida property, no competitor domain detected — all 14 checks pass. Agent 5 pulls the county-adjusted price from Field to Finish: 350 dollars.

---

## Scene 7 — Human Approval Gate  [01:33 – 01:55]

> For complex orders, Agent 4 sends a structured notification to the FTF-Approvals Teams channel. All pending orders are listed together — with their FTF links, estimates, service types, and property addresses. Robert, Ryan, or Prateek reply directly in the thread. No portal login. No emails back and forth.

---

## Scene 8 — Teams Approval Commands  [01:55 – 02:20]

> The approval interface handles any command format. Type APPROVE and the bot auto-detects the single pending order. For multiple orders: APPROVE order-1 comma order-2 — commas and spaces both work. You can even mix approve and reject in one message. After each action, the bot immediately lists what orders are still waiting for a decision.

---

## Scene 9 — Decision Reversal  [02:20 – 02:45]

> What if Ryan approves an order and Robert disagrees? The bot asks for confirmation before changing any final decision. It posts: this order was approved — do you really want to reject it? Reply YES or NO. Common phrases all work — yeah, nope, go ahead, keep it. Every decision, original and override, is logged with timestamp and sender name.

---

## Scene 10 — Daily 9 AM Reminder  [02:45 – 03:04]

> What if nobody replies by end of day? Every weekday at 9 AM the bot re-posts all unanswered orders with the original pending timestamp and how many days ago they were submitted. It repeats every working day, automatically, until every order has a decision.

---

## Scene 11 — GitHub Actions 24/7  [03:05 – 03:33]

> The entire approval system runs automatically — no local machine, no manual script. GitHub Actions fires the polling workflow every 5 minutes, around the clock. It reads the Teams channel, processes any APPROVE or REJECT commands within minutes, and posts confirmations back. The daily reminder fires at 9 AM weekdays automatically. Twelve secrets wired in. Zero infrastructure to maintain.

---

## Scene 12 — Write, Review & Send  [03:34 – 04:02]

> Back to John. Agent 6 drafts a personalized estimate email with his name, property address, and the exact service requested. Agent 7 runs 4 accuracy checks: price match, client name, address verification, and change order clause. All 4 pass. Agent 8 delivers the quote to John's inbox. From order detected to email sent — under 2 minutes. No one on your team touched a thing.

---

## Scene 13 — Sprint 9 — Memory Loop  [04:02 – 04:32]

> Sprint 9 adds three things the pipeline was missing. A real-time database listener: the instant Agent 2 saves an order, a PostgreSQL trigger fires and the full pipeline runs immediately. A nightly memory log: every decision every agent made, written to a structured file. And a 7-day pattern analyzer that flags any agent falling below 90 percent accuracy. The system now watches itself.

---

## Scene 14 — AR Report Skill  [04:32 – 04:55]

> We also built a live accounts receivable skill. Every morning it logs into FTF Books, downloads the full unpaid invoice list — over 2,100 invoices in the Books module, 78,000 records accessible via the REST API — and builds a two-tab Excel report with aging buckets and a pivot summary.

---

## Scene 15 — Sprint 10-12 Roadmap  [04:55 – 05:19]

> Here is what comes next. Sprint 7 automates AR follow-up reminders for overdue invoices. Sprint 8 generates monthly statements automatically. Both are ready to build the moment Jessica and Wyatt record their current process. Sprint 10 is the full staging test, followed by a limited launch, and then full production.

---

## Scene 16 — Summary  [05:20 – 05:56]

> To summarize what has been built. 9 AI agents handling your entire quoting pipeline. 203 automated tests keeping every component verified. A smart Teams approval channel that handles every decision scenario automatically. 24/7 automated monitoring via GitHub Actions — no manual intervention required. Orders that used to take 5 hours now complete in under 2 minutes. Your process runs automatically, reports on itself, and scales with your volume. Thank you for your time.

---
