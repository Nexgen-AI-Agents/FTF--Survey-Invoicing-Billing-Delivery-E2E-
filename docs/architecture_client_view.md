# NexGen AI Invoice System
## Client Overview — How It Works
*Non-technical. Plain English.*

---

## The Problem We're Solving

Right now, every time a client orders a survey, someone on your team has to:
1. Find the order in the system
2. Hunt through emails and chat messages to figure out exactly what was requested
3. Build the invoice manually
4. Email it back and forth for review
5. Send it to the client

This takes hours — sometimes days — and only happens during business hours. Orders sit overnight. Clients wait.

**The AI system does all of this automatically, 24 hours a day.**

---

## How an Order Flows Through the System

```
CLIENT                          YOUR TEAM                        AI SYSTEM
  │                                 │                                │
  │  Sends email or submits         │                                │
  │  order via portal ─────────────►│                                │
  │                                 │  Creates order in FTF          │
  │                                 │  system with $ flag ──────────►│
  │                                 │                                │ 1. Sees the $ flag
  │                                 │                                │    (every 15 min scan)
  │                                 │                                │
  │                                 │                                │ 2. Reads the order
  │                                 │                                │    Searches emails
  │                                 │                                │    Reads Teams chat
  │                                 │                                │    Builds full picture
  │                                 │                                │
  │                                 │◄───────────────────────────────│ 3. Posts invoice draft
  │                                 │  "Here's what I found.         │    to Teams group chat
  │                                 │   Order 12345 — John Smith     │
  │                                 │   123 Main St, Miami           │
  │                                 │   Land Survey Only — $450      │
  │                                 │   Ready to send?"              │
  │                                 │                                │
  │                                 │  Robert/Ryan/Prateek           │
  │                                 │  reviews in Teams              │
  │                                 │                                │
  │                                 │  Option A: Reply "APPROVE"    │
  │                                 │  ──────────────────────────── ►│ 4a. Creates invoice in FTF
  │                                 │                                │     Sends email to client
  │◄───────────────────────────────────────────────────────────────  │
  │  Receives professional                                            │
  │  invoice email                                                    │
  │                                 │  Option B: Reply "change       │
  │                                 │  price to $500"               │
  │                                 │  ─────────────────────────── ►│ 4b. Updates draft
  │                                 │◄───────────────────────────── │     Reposts to Teams
  │                                 │  "Updated. Total now $500.     │     "Anything else?"
  │                                 │   Still approve?"              │
  │                                 │                                │
  │                                 │  Option C: Reply "REJECT"     │
  │                                 │  ─────────────────────────── ►│ 4c. Holds order
  │                                 │                                │     Does NOT send to client
  │                                 │                                │     Waits for next instruction
```

---

## What the AI Does (and Does Not Do)

### The AI does:
- Watches for every order that needs an invoice — 24/7, not just 9–5
- Reads the order details from your FTF system
- Searches your email inbox (`nesa@nexgenlogix.com`) for related client emails
- Reads your Teams group chat for messages about that order
- Builds a complete invoice draft with services and pricing
- Posts the draft to Teams and explains what it found and what it's unsure about
- Updates the draft based on your team's feedback (plain English — no special commands needed)
- Creates the final invoice in FTF once approved
- Sends a personalized email to the client
- Learns from every correction so it gets better over time

### The AI does NOT:
- Send any invoice to a client without explicit approval from Robert, Ryan, or Prateek
- Make pricing decisions without showing its work
- Handle refund requests — those always go to Jessica immediately
- Touch any order that's already been invoiced

---

## What Your Team Does

Your team's only job in this pipeline is to **review and respond in Teams**. That's it.

You can reply to the AI's message with:
- **"Approve"** — send it as-is
- **"Change price to $X"** — AI updates and reposts
- **"Add elevation certificate"** — AI adds the service and recalculates
- **"Remove X"** — AI removes and recalculates
- **"Reject"** — hold the order, don't send to client
- Any question or instruction in plain English — the AI will interpret it

The AI will ask you a question back if it's confused about anything.

---

## The Learning System

Every time your team makes a correction ("change this price," "always add this service for flood zone properties"), the AI stores that as a rule. Next time it sees a similar order, it applies the lesson automatically. Over time, the AI needs fewer corrections because it's learned your team's judgment.

This learning is permanent — it builds up with every order processed.

---

## What This Means for Your Business

| Before AI | After AI |
|-----------|----------|
| Invoice built manually: 30–60 min per order | Invoice drafted automatically in ~3 min |
| Only during business hours | 24 hours a day, 7 days a week |
| Human must hunt through emails + chat | AI searches all sources automatically |
| Invoice sent only when someone remembers | Every $ flag cleared within hours |
| Corrections never saved | Every correction becomes a permanent rule |
| Client waits overnight for invoice | Client receives invoice same-day or next morning |

---

## Phase 1 Scope (What's Live Now)

Phase 1 ends the moment the invoice email is sent to the client. Everything in this document is Phase 1.

**Not included in Phase 1** (coming later):
- Automatic payment reminders (Phase 2)
- Monthly statements for business clients (Phase 2)
- Upsell campaigns (Phase 2)
- Website chat integration (Phase 3)
