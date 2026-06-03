# NexGen AI Invoice System — Client Overview
*Plain English. No technical jargon.*
Last updated: 2026-06-03

---

## The Problem We're Solving

Every survey order that comes in needs an invoice. Someone has to:
1. Find the order
2. Look up what was requested (emails, chat, order notes)
3. Price it correctly
4. Get approval from Robert, Ryan, or Prateek
5. Send the invoice to the client

This used to take hours — and only happened during business hours. Now the AI does it automatically, 24 hours a day, 7 days a week.

---

## How an Order Flows Through the System

```
CLIENT                     YOUR TEAM                    AI SYSTEM
  │                             │                            │
  │  Orders a survey            │                            │
  │  (web, email, phone)        │                            │
  │                             │  Sets invoice_needed       │
  │                             │  flag in FTF ─────────────►│
  │                             │                            │ Sees the flag
  │                             │                            │ (every 30 min scan)
  │                             │                            │
  │                             │                            │ Reads order from FTF
  │                             │                            │ Searches email inbox
  │                             │                            │ Checks county records
  │                             │                            │ Prices the job
  │                             │                            │
  │                         ◄───────────────────────────────│ Posts invoice draft
  │                             │  Order 1000273343           │ to Teams channel
  │                             │  Johanne Beaumont           │
  │                             │  Land Survey Only — $475   │
  │                             │  [Approve] [Reject]        │
  │                             │  [Feedback]                │
  │                             │                            │
  │                             │  Robert / Ryan / Prateek   │
  │                             │  replies in Teams          │
  │                             │                            │
  │                             │  "Approve" ───────────────►│ Creates FTF invoice
  │                             │                            │ Sends email to client
  │◄────────────────────────────────────────────────────────│
  │  Receives invoice email                                   │
  │                             │                            │
  │                             │  "Change price to $500" ──►│ Updates draft
  │                         ◄───────────────────────────────│ Reposts in Teams
  │                             │  "Updated to $500.         │
  │                             │   Approve?"                │
  │                             │                            │
  │                             │  "Reject" ────────────────►│ Holds order
  │                             │                            │ No email sent
```

---

## The 8 AI Agents — What Each One Does

| Agent | Plain English Name | What It Does |
|-------|--------------------|--------------|
| **A0** | The Manager | Wakes up every 30 minutes and tells all other agents to do their jobs in order. |
| **A1** | The Flag Hunter | Scans every order in FTF looking for the "invoice needed" flag. Queues them for processing. |
| **A2** | The Researcher | For each queued order: reads FTF order details, searches the email inbox, looks up the county property record, checks Google Maps. Builds a complete picture of the job. |
| **A3** | The Pricer | Uses all the research plus your past corrections to price the job. Explains its reasoning. Posts the invoice draft to Teams for your approval. Retries up to 2 times if the AI response is incomplete before escalating. |
| **A4** | The Listener | Watches your Teams replies every 2 minutes. Understands plain English — "approve", "change the price", "hold this", "reject". Acts on your instructions. |
| **A5** | The Invoice Creator | When you approve: creates the official invoice inside FTF and records the invoice number. |
| **A6** | The Sender | Sends a personalized invoice email directly to the client on NexGen letterhead. |
| **A7** | The Learner | Reads your Teams feedback (even comments that aren't approve/reject). Extracts pricing rules and remembers them for next time. |

---

## What Your Team Does

Your team's only job is to **reply in Teams**. That's it.

The AI posts a card in the Teams channel for every order. You reply with:

- **Approve** — AI creates FTF invoice and sends email to client
- **Reject** — AI holds the order, does not send to client
- **Change price to $X** — AI updates draft and reposts, asks again
- **Add elevation certificate** — AI adds service and recalculates
- **Hold this** — AI pauses without rejecting
- Any plain English instruction — AI interprets and acts

The AI replies in the same thread confirming what it understood. If it's unsure, it asks a clarifying question.

Only **Robert, Ryan, and Prateek** can trigger approve/reject/modify actions.

---

## When the AI Can't Determine the Price

Occasionally the AI posts an **ESCALATED** card. This happens when:

- The order is unusually complex (lot > 5 acres, commercial, custom legal description)
- The AI's pricing response was incomplete after 3 attempts
- The service type does not match any known pattern

**What to do:** Reply to the escalated card with the correct price or service details (e.g., "Land Survey Only at $475"). The AI will update the draft and repost the approval card.

---

## The Learning System

Every time your team corrects the AI ("change price to $X", "always add EC for flood zones"), the AI:
1. Stores the correction as a rule
2. Applies that rule automatically to similar orders next time

Over time, the AI needs fewer corrections because it has learned your team's judgment.

---

## Two Speeds

The system runs at two speeds to be both thorough and fast:

| Speed | How Often | What It Does |
|-------|-----------|--------------|
| Full pipeline | Every 30 minutes | Discovers new orders, researches them, prices them, posts to Teams |
| Reply check | Every 2 minutes | Checks if you've replied to any pending approval cards |

This means after you reply "Approve" in Teams, the invoice is created and email sent within 2–4 minutes.

---

## What the AI Does NOT Do

- Send any invoice without explicit approval from Robert, Ryan, or Prateek
- Touch any order that is already invoiced
- Handle refund requests — those go directly to the team
- Make pricing decisions without showing its reasoning in Teams

---

## Business Impact

| Before AI | After AI |
|-----------|----------|
| Invoice drafted manually: 30–60 min | Drafted automatically in ~3 min |
| Business hours only | 24 / 7 |
| Price from memory or spreadsheet | Priced from 18,000+ real orders + learned rules |
| Corrections lost after the call | Every correction saved as a permanent rule |
| Client waits overnight | Client receives invoice same day |
| Invoice only if someone remembers | Every flagged order cleared within hours |

---

## Current Pipeline Status (as of 2026-06-03)

| Stage | Count |
|-------|-------|
| Waiting for your Teams approval | ~121 |
| Being researched / priced | ~80 |
| Flagged in FTF — not yet started | ~116 |
| Missing client details | ~61 |
| Sent to client | growing |

Most of the "waiting for approval" orders were queued during pipeline testing. Once email delivery is enabled, approvals will clear rapidly.

---

## Scope

**Phase 1 (live now):** Find order → research → price → Teams approval → FTF invoice → email to client.

**Phase 2 (planned):** Payment follow-up reminders, AR aging reports, monthly client statements.
