# Extracted Points — Ryan & Prateek 45min Call
**Date:** Tue, May 26, 2026
**Raw file:** [2026-05-26_ryan-prateek_45min.txt](../raw/2026-05-26_ryan-prateek_45min.txt)
**Extraction status:** ✅ Complete — issues logged I-055 through I-066

---

## 1. Demo Fixes
**Timestamp:** 1:58 Ryan
- "50 orders a week" → **"a lot of orders a week"** — too specific, needs to be generic for any client audience
- Competitor flag narration not explained — viewers didn't understand why a competitor check happens
  - Should explain: AI detects if a quote might be from a competitor → routes to manual review, not auto-quoted
- **Actioned:** I-059 (closed), I-060 (closed). Fixed in Demo v7.

---

## 2. Quote → Pending Conversion via Email (NEW AGENT)
**Timestamp:** 3:19–5:00 Ryan
> "There should be an agent that's monitoring the info emails...any email that says convert this or approved or whatever, that it would know it would read the whole email, figure out what it's approving, and then go and send a message to the team letting them know that it moved to pending."

- Agent watches **info@nexgensurveying.com** for customer approval emails
- Keywords: "approved", "go ahead", "convert", "move forward"
- AI reads full email → identifies which order/property → moves quote→pending → notifies team
- **Hard rule:** If cannot identify order/property → flag for human review, do NOT auto-convert
- **Actioned:** I-061 (closed). Agent 12 built in Sprint 5.

---

## 3. Website Chat → Order Conversion
**Timestamp:** 4:07–5:00 Ryan
> "If they can go onto our website and use our chat and ask it to go ahead and move forward with this. And it maybe says, well, what's the property that we're moving forward with? Can you give me the exact address?"

- Customer goes to website chat → says "I want to proceed"
- AI asks: property address OR order number
- If neither provided → AI asks again, cannot convert without one
- If provided → convert quote to pending, notify team
- **Actioned:** I-062 (OPEN — website chat integration not yet built, Sprint 6+)

---

## 4. Refund Hard Rule
**Timestamp:** ~8:00 Ryan
> "We don't want AI doing a refund."

- Any refund request → **Jessica notified immediately, she handles manually**
- AI never touches, processes, or approves a refund — ever
- Same class as NEVER_AUTO_QUOTE rule
- **Actioned:** I-063 (closed). refund_guard.py built.

---

## 5. Bobby Hourly Approval Digest
**Timestamp:** 28:22 Ryan
> "As soon as we can release this to Bobby and have it automatically every hour send him a list of files that are linked...the job size, a brief description, the estimate total with a column for approved or denied."

- Hourly Teams message with ALL pending orders: clickable FTF link, service type, amount, flag reason, Approve/Deny
- Bobby can approve all at once or pick specific ones to deny manually
- **NOT per-order pings** — one batched digest per hour
- **Actioned:** I-064 (closed). send_batch_approval_digest() built in Sprint 3.

---

## 6. Dynamic Pricing Factors
**Timestamp:** 10:09–13:20 Ryan
> "Same half-acre with a pool, multiple driveways, shed, back patio = $700. Same half-acre, plain house = $350."

| Factor | Impact |
|--------|--------|
| Swimming pool | Significant upcharge |
| Number of walls/corners (30 vs 4) | More time → higher price |
| Back patio | Moderate upcharge |
| Shed(s) | Per shed upcharge |
| Multiple / looping driveways | Upcharge |
| Far from crew location | Travel cost → higher price |
| Remote area (top of state) | Charge more |
| Crew schedule + location | Future: reference availability and proximity |

- **Actioned:** I-065 (closed). Factors documented in florida_pricing_intelligence.md. Code gated by PRICING_COMPLEXITY_ENABLED=false until Robert confirms weights.

---

## 7. Historical Invoicing Reference
**Timestamp:** ~10:00 Ryan
> "Take the last 1-2 years. We don't have to go back 10 years."

- Load last 2 years of FTF invoices into AI pricing context
- AI references these when pricing similar jobs
- Bobby/Robert can describe a job like a past invoice → AI stores it
- **Actioned:** I-066 (closed). fetch_historical_pricing.py built.

---

## 8. AI Training Interface — Role-Based
**Timestamp:** 17:23 Ryan
> "Bobby would be able to say, this is how I would bill for this and why, and the AI should store it."

- Bobby trains AI on pricing/logistics judgment calls via chat or CLI
- Jessica trains AI on AR process modifications
- **Role-based:** Bobby cannot modify refund process. Jessica cannot modify field quoting.
- Cross-domain changes require both parties + Prateek notification
- **Actioned:** I-067 (closed). Agent 13 Pricing Trainer + roles.py built. I-065 role-based access.

---

## 9. Everything to Manual Review — Current Phase Rule
**Timestamp:** 19:12 Ryan
> "Right now, we would want to send everything for manual review for us to be able to say approved or not."

- **CONFIRMED DECISION:** ALL quotes go to human review before anything is sent to client
- This relaxes over time as confidence builds — not forever
- Actioned: confirmed in memory.md Confirmed Decisions.

---

## 10. Florida PSM Standards — AI Knowledge Base
**Timestamp:** 22:05 Ryan
> "Did you feed it the Florida standards for licensed surveyors? Create a persona of a high-performing Florida surveyor."

- Feed FL Professional Surveyor and Mapper (PSM) standards (Chapter 5J-17 FAC) to AI
- AI answers from two angles: (1) FL PSM technical, (2) NexGen perspective
- **Actioned:** I-068 (closed). florida_psm_standards.md + fl_psm_persona.txt built.

---

## 11. Weather Monitoring Agent — Future Sprint
**Timestamp:** 40:35 Ryan
> "The AI already checked the weather, knows where it's going to be, knows what orders it's going to affect, and sends a suggestion — automated email to send out to all customers that may be affected."

- Daily: check weather for all active order locations
- Identify orders at risk of delay
- Draft proactive delay-notice email to affected customers
- Send to Bobby/Ryan for approval before dispatching
- **Status:** Future sprint — not scheduled yet.

---

## Skipped (Not FTF Relevant)
- Ryan's personal AI assistant ideas (coffee maker, grocery list, etc.)
- Cross-AI communication between Ryan's and Prateek's AI instances
- General business philosophy on entrepreneurship
- Video demo quality vs. Synthesia comparison (non-technical)
