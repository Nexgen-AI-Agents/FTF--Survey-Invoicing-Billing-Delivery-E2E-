# Extracted Points — Ryan & Prateek: Agentic AI, Hermes, Upsell Strategy
**Date:** Mon, May 25, 2026
**Raw file:** [2026-05-25_ryan-prateek_agentic-ai-hermes-upsell.txt](../raw/2026-05-25_ryan-prateek_agentic-ai-hermes-upsell.txt)
**Extraction status:** ✅ Complete — new issues logged I-090 through I-092

---

## 1. Upsell Campaigns on Active Orders (NEW — I-070)
**Timestamp:** 2:33, 44:04 Ryan
> "Three to five products upsell...send the estimate, but also on quotes, maybe it starts sending follow-ups with additional things that could be added."

- After estimate is sent to customer → run a follow-up email campaign asking upsell questions
- Suggested upsells per order:
  - Rush fee ("Do you need this faster?")
  - Aerial/additional photos of property
  - Elevation Certificate (if not already auto-added by flood zone check)
  - Future survey update
- 3–5 follow-up emails during the order cycle (not after delivery)
- Pricing for each upsell item must be defined first (Ryan + Robert to confirm)
- **Issue logged:** I-090 (OPEN) — Sprint 13

---

## 2. Re-Engagement Email Campaign for Inactive Customers (NEW — I-071)
**Timestamp:** 37:51 Ryan
> "Anybody who hasn't ordered from us in the last six months or longer...reach out to somebody who already knows that person, who's already used that person, to re-engage."

- Pull all customers who haven't ordered in **1+ year**
- Run a re-engagement email sequence: 1/week → 2/week → 3/week (escalate until response or unsubscribe)
- Reintroduce NexGen, mention they've worked together before
- Ryan's logic: "If we're pissing them off, who cares — they don't order from us anyways. Keep adding until it breaks, then roll back."
- GoHighLevel (GHL) or direct email campaign — evaluate platform
- **Issue logged:** I-091 (OPEN) — Sprint 13

---

## 3. GoHighLevel (GHL) for Campaign Pipelines (NEW — I-072)
**Timestamp:** 46:29 Prateek, 47:05 Ryan
> "We have a person on our team who worked on GHL. If we can discuss the requirement, he can start building funnels, pipelines in GHL."

- Prateek's QA person knows GoHighLevel — can build campaigns
- Ryan wants to evaluate: internal GHL person cost vs. GHL specialist contractor
- Decision: test GHL internally first, evaluate output quality vs. cost
- Not blocking any current sprint — parallel workstream
- **Issue logged:** I-092 (OPEN) — Ryan to confirm budget/approach

---

## 4. Competitor List — Three Missing Competitors (FIXED — I-073)
**Timestamp:** 39:43 Ryan
> "The analysis is missing a few: Exacta, Landtech Surveying and Lien, and Target Surveying."

- AI competitor analysis missed 3 major FL competitors:
  - **Exacta Land Surveyors** — Ohio-based, 3 FL offices (Oviedo FL is one)
  - **Landtech Surveying and Lien LLC** — Ryan almost bought in 2017; David Zyd, Ryan Soules et al.
  - **Target Surveying** — Founded by Clyde, sold to employees; active competitor
- GT Surveying found but irrelevant (tiny — ex-NexGen employees, Gino's company)
- **Status:** Already added to flag_triggers.py per I-041 (closed 2026-05-27). Confirmed complete.

---

## 5. Multi-Model Architecture Confirmed (Prateek)
**Timestamp:** 30:37 Prateek (May 26 45min call overlap context)
- Hermes (Ollama local): low-complexity tasks
- Claude Sonnet: high-complexity classification, writing, review
- OpenAI (TTS/GPT): media generation (demos, voiceover)
- Plan to add 1–2 more free/secure LLM models as fallback
- Obsidian: second brain / visual knowledge graph (already integrated)
- **Status:** Architecture confirmed. No new issues — already in system design.

---

## 6. Hybrid Automation Philosophy — Ryan's Explicit Confirmation
**Timestamp:** 2:33 Ryan
> "It's automated, but at certain points it sends Teams messages and just asks these couple questions here and there based on its learning."

- Ryan explicitly confirmed: hybrid model is correct
  - Automate the routine → surface the exceptions → human decides → AI learns
- NOT fully autonomous at this stage — human-in-the-loop is the design, not a limitation
- Over time: reduce the human checkpoints as confidence builds
- **Status:** Confirms existing architecture. No code change needed.

---

## 7. AI Should Learn From Team Continuously (Memory/Training Loop)
**Timestamp:** 8:56 Ryan
> "Once we deploy something like this, it needs to constantly get trained. How do we teach them to train it? How do we check in with them every month or so?"

- Monthly check-in cadence with stakeholders (Ryan/Bobby/Jessica) to review AI performance
- Stakeholders train AI by describing real jobs: "This job is like invoice X, here's why we priced it Y"
- AI stores it and uses it in future pricing context
- **Status:** Agent 13 (Pricing Trainer) built in Sprint 9. Monthly check-in process not yet formalized — needs a calendar event or cron-based prompt.

---

## 8. Sprint Status at Time of Call (May 25, 2026)
- 4 sprints complete
- Robert's recording just received that morning (May 25)
- Jessica's recording: waiting, was supposed to be Wednesday, then Thursday — holiday Monday so chasing Tuesday
- Prateek's target: show Ryan something by May 26 EOD

---

## Skipped (Not FTF Relevant)
- Ryan's personal AI assistant (Hermes for home: coffee maker, groceries, dog)
- Cross-AI communication between Ryan's and Prateek's personal AI instances
- NGE staff incentive discussion (Thomas report, $600K Q2 target — internal NGE, not FTF)
- Wyatt's report discrepancy ($300K difference) — NGE AR report, not FTF invoicing
- Ryan's business philosophy monologue (surveyor overthinking customer needs)
- GHL personal assistant concept for executives (future product idea, not FTF)
- "Sell skills on website for $100" — NGE product idea, not FTF scope
