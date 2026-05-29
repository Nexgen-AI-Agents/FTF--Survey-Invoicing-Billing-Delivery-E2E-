# Transcript Extract — Ryan & Prateek Connect
**Date:** 2026-05-29 (~45 min)
**Raw:** `transcripts/raw/2026-05-29_45mins - Ryan and Prateek Connect Transcript(1)`
**Extracted by:** Claude Code 2026-05-29

---

## Context

Prateek testing the full AI OS end-to-end and it broke at multiple places due to ambiguous order handling. Called Ryan to clarify the exact process. Ryan clarified the estimate OS scope, approval flow, and introduced NESA concept.

---

## Key Decisions & Clarifications

### 1. Estimate OS Goal — FLAG HUNTER (not status tracker)

Ryan (verbatim): *"Its only goal is to make sure the invoices are generated and all the clients got their generated invoices. It's focused on the flag more than the status. The flag that the dollar sign flag — if the invoice has been delivered, it goes away. But if the invoice has been generated but not delivered, it's still a little dollar sign still shows up in the flag section. That's what this estimating agent, its goal in life is to make sure that at the end of every day, there are none of those flags in the system of uninvoiced or unestimated delivered."*

**Change Required (I-093):** Agent 2 must scan ALL orders for missing-invoice flag, not just Quote status.

---

### 2. Post-Invoice: Agent Is Done

Ryan: *"Once they approve it, then we go, right? And then the manual aspect of like the people looking at the jobs and the crews going out to the field and all that stuff. If something else happens that we need to make an adjustment, we just go in there and make an adjustment. This AI is already out of the process, right? It's already been invoiced, so it's not looking at the file anymore because the flag's gone. It doesn't care at that point."*

**Confirmed Decision:** After invoice delivered = agent stops. No post-send tracking in estimate OS.

---

### 3. Approval Flow: Price Adjustment Allowed

Ryan: *"We do want the user to be able to adjust the approval, right? So it sends a message $400 estimate, and you say, make it $500. And it would be okay, I need to make an adjustment. So then the next time it does that same file, it's going to start at 500 probably because it's learning."*

**Change Required (I-094):** Add ADJUST $X command to Human Gate. AI learns from adjustments.

---

### 4. Personalized Email on Delivery

Ryan: *"What I wanted to do is to deliver the invoice that was approved and just be personalized and try and maybe upsell and ask for a review on every email."*

**Change Required (I-095):** Agent 6 Writer + Agent 8 Sender must personalize email body/subject per client, include upsell offer, include Google review ask.

---

### 5. Parallel/Shadow Mode First

Ryan: *"Everybody's going to be running everything exactly how it is. And this thing's be running and giving us suggestions on the estimates and all that stuff. And we're going to talk about it at first. See how it's, you know, how we could be, you know, if we were saying approved all these things, what would that look like compared to what's actually happening? It'd be really cool to see at the end of a day of that estimating feature happening, you know, totalizing everything and having it kind of generate like an end-of-day report."*

*"If it's way lower, then it gives us the ability in the beginning to just say, okay, whatever you're thinking, adjust your pricing up 20%."*

**New Feature (I-096):** Shadow mode deployment. AI estimates but does not send. End-of-day comparison report. Enables calibration before live.

---

### 6. NESA — NexGen Enterprises Surveying AI

Ryan: *"Next gen enterprises surveying AI."* (when explaining the name)

Ryan on NESA behavior: *"NESA is going to be a highly capable blank slate. Right. But as Bobby talks to it and asks it to, like, hey, can you go find this? It goes and finds something wrong. And it's, and Bobby goes, no, that's not it. This is what it is, and works through, you know, and it's learning. Then, what is it? A month, two months, three months."*

Ryan on timeline: *"Next week, we'll see if we can do it. See what we can come up with."*

Ryan on scope: *"Yeah, can we prompt it to do this and that and have it do some emailing and follow-ups and things like that?"*

**New Feature (I-097):** NESA agent. Blank slate. Learns from Bobby interactions. Access to FTF + Teams + email. Starts Sprint 12.

---

### 7. Small Agents Philosophy

Ryan: *"Make it into another little AI that just does this one thing, right? Because it's really about having a bunch of small, focused, dedicated to one thing AI and then manage them more than it is about having one AI that's really good."*

Ryan: *"If one of those managed agents breaks, it can still go through the rest of the agents and finish the process without certain ones, versus if you build it into one agent and it breaks, it just stops."*

**Confirmed:** Architecture direction — many small focused agents managed by one high-level agent. Estimate OS: each agent does ONE thing. No bundling.

---

### 8. Summit's Future Role

Ryan: *"Summit gets like clogged. Right? Maybe that's something that we just go ahead and give Summit. And then Summit needs to be, and I said the intention is to have the whole team in the chat. So, you know, just understand that Summit would be in the chat reviewing too. But then Summit could have the chance of really dialing in a claw and helping critique on the logistics claud."*

Ryan: *"At scale, you know, Summit should be probably in charge of the logistics and the estimating agents."*

**Confirmed:** Summit will manage NESA + logistics agents. May also learn AutoCAD + customer interaction.

---

### 9. Win-Back Email Agent

Ryan: *"The idea of following up on every job that has, you know, any customer that hasn't ordered anything in a year or more. How long would it take? That's a very simple concept, right? Very direct process."*

Ryan on approach: *"It's like a tortoise. It's just never-ending, sending emails to these people in a, in a, in a slow enough way that it doesn't trigger spam. If somebody replies back, it lets us know, and it just keeps going."*

Ryan: *"If that only takes an hour to build, then doing that is more effective from a business perspective for the customer while we upsell why go high-level would be better."*

**New Feature (I-098):** Win-back agent. Staggered, personalized, slow. FTF API first. GHL upgrade later for tracking.

---

### 10. In-Progress / In-Revision Status

Ryan: *"Somebody, if somebody clicks in revision, it highlights the file pink in track flow. They're currently using that for the purpose of what in progress is for."*

Ryan: *"The in revision button is so much less useful than the highlight function. They're just sticking to their old ways."*

**Status:** Not in current sprint scope. Ryan wants to use NESA to eventually fix this habit. Track under existing I-046.

---

## Quote → Pending Flow (Confirmed)

Three channels for quote approval:
1. Client emails reply with keywords ("approved", "go ahead", "move forward") → Agent 12 detects + converts
2. Client logs into portal → converts quote to pending from order history
3. Client calls → staff member manually changes status in FTF

---

## Things NOT in This Project (Ryan explicitly or contextually)

- Post-invoice order modifications (manual, agent is out)
- What happens after pending (logistics agent — future)
- Crew scheduling, job board, job posting (logistics agent — future)
- Ranking crews or files (future agents, sub-components of logistics)
- Marketing agent / no-conversion follow-up (future, needs estimate OS logs first)
- GHL full integration now (upgrade path, not current)
- Podcast from transcripts (personal interest, not project work)
- In-revision/in-progress status cleanup (after NESA)

---

## Open Questions for Ryan

1. NESA: what does it connect to on day 1 — FTF only, or also Teams/email/files?
2. Parallel mode: AI suggests in Teams but does NOT generate/deliver invoices, or generates draft-only?
3. Win-back agent: which email system — FTF Books API or separate SMTP?
4. ADJUST command: does AI update FTF invoice price before sending, or just note it for learning?
5. Personalized email: replaces FTF built-in Deliver email, or is it a custom email sent in addition?
6. Summit managing NESA: does this change any current approval flow (does Summit get approvals instead of Bobby/Robert)?
7. End-of-day comparison report: where does it go — Teams channel, email to Ryan/Bobby, or both?

---

## Issues Created From This Transcript

| Issue | Title |
|-------|-------|
| I-093 | CR: Agent 2 Monitor scan ALL orders for invoice flag |
| I-094 | CR: Agent 4 Human Gate ADJUST $X command |
| I-095 | CR: Personalized email + upsell + review ask on delivery |
| I-096 | New Feature: Parallel/shadow mode |
| I-097 | New Feature: NESA agent |
| I-098 | New Feature: Win-back email agent |
| I-099 | Research: Hermes Agent platform for NESA |
