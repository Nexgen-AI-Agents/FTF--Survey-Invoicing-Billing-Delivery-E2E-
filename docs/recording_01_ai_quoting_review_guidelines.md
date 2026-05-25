# Recording 01 — AI Quoting & Review Process Guidelines

**Source:** Screen recording "AI Quoting and Review Process Guidelines" (24 min, 1449 frames)
**Extracted by:** AI frame analysis (every 5–30 frame sampling + high-res crops of all content sections)
**Document title on screen:** `Questions_Robert_Mark` (SharePoint Word doc)
**Prepared by:** Prateek | May 2026
**Classification:** FTF Agentic AI | Robert & Mark | Confidential

---

## Verbal Answers (from audio transcript)

**Source:** Robert verbal Q&A session, Recording 1 audio transcript. Confirmed 2026-05-25.

### Section 2 — Service Type Name Mappings (CRITICAL — now answered)

| Question | Robert's Answer | Status |
|----------|----------------|--------|
| What is Topographic Survey called in FTF? | "Topographic Survey" or "Topographic Boundary Survey" — brand new from-scratch = "Topographic Boundary Survey"; update/topo only = "Topo Survey", "Topographic Survey", or "Update/Topographic Survey" | **ANSWERED** |
| What is Construction Survey called in FTF? | Maps to Topo Survey (design phase); building stakeout / form board / foundation tie-in are the DURING-construction sub-services | **ANSWERED** |
| What is Permitting Survey called in FTF? | Still a Boundary Survey but with 3rd-party digital signature added; "Permitting" = that digital signature requirement for county portal uploads | **ANSWERED** |
| Specific Purpose Survey vs Special Purpose Survey? | Interchangeable — Robert uses "Specific Purpose Survey" | **ANSWERED** |

### Section 3 — Services NGE Does / Does Not Do (now answered)

**Services NGE DOES perform:**
- Boundary Survey, Topographic Survey, Topographic Boundary Survey
- Form Board Survey, Spot Survey, Foundation Tie-In Survey (aka Spot/Foundation)
- As-Built Survey
- Specific Purpose Survey / Special Purpose Survey
- Elevation Certificate
- Plot Plan

**Services NGE does NOT do (never auto-quote):**
- Engineering services / drainage design
- Site Plans (should be architects/engineers)
- Wetland Delineation — needs specialist engineer, too complex; add to never-auto-quote
- Building Stakeout — NGE is "dabbling" in it again (treat as flag-for-human-review until confirmed; see I-041)

### Section 3 — Flagging Rules (partially answered)

- ALTA Table A Survey: always human review (confirmed)
- B-II Title Review: always human review (Robert confirmed)
- Wetland Delineation: always human review / never auto-quote
- Lot Split: always human review (implied by management-level review rule)
- Competitor list: Robert confirmed it exists; will write it up — still pending (I-040)
- Robert said he ALWAYS personally reviews every estimate — AI should SUGGEST and ROUTE for approval, NOT auto-send blindly (see I-043)

### Section 4 — Geographic Rules (now answered)

- Florida only (for now)
- All 67 FL counties can be quoted
- Monroe County (Florida Keys): flag for extra review, charge more, limited crew — already built (I-034)
- Panhandle / northwest FL: they struggle with crew but still quote
- Vero Beach: having issues but manageable
- Jacksonville, St. Augustine, Orlando, South/Southeast/Southwest FL: good coverage

### Section 5 — Change Order Clause (now answered)

- Currently NO change order language in estimates — this is completely new (BRD Amendment 001)
- Communication process: call/contact client first → explain scope change → get verbal/email OK → THEN add to invoice
- Should never be auto-added without client confirmation
- Change order clause text to be drafted by Ryan (I-042)

### Section 5 — Customer Approval Workflow (now answered)

Most to least common:
1. Client pays invoice via payment link → auto-advances to "pending"
2. Client emails confirmation ("please proceed" / "we accept")
3. Client accepts via FTF portal
4. Phone call (Robert asks for email follow-up)

### Still Open / Pending

| Item | Status |
|------|--------|
| Competitor list (do-not-auto-quote companies) | Robert will write it up — I-040 |
| Building Stakeout confirmed back in service? | Ambiguous — I-041 |
| Change order clause exact text | Ryan to draft — I-042 |
| Past dispute history (Section 5 row 3) | Not yet provided |

---

## Executive Summary

This recording contains a Q&A intake document Robert and Mark must fill in so the AI quoting pipeline can be built. The document is structured as a table with columns **Priority**, **What We Need From You**, and **Your Answer** (blank — to be filled by Robert/Mark).

It covers five sections:

1. Recording sessions (Robert/Mark must record themselves doing the full quoting workflow)
2. Survey names in the FTF system (exact service name mappings)
3. Flagging rules (which orders the AI must NEVER auto-quote)
4. Specific services that need special handling
5. Change order clause requirements (new — BRD Amendment 001)

The recording also includes a live demo of the FTF order system showing the Flood/Hazard Zone panel, FEMA Flood Map Service links, and the quote PDF output. It includes a Google Earth segment showing Florida geography (likely discussing service territory context — Monroe County/Keys, counties NGE operates in).

**Key finding:** This document is a *requirements intake form*, not a completed rules spec. The "Your Answer" column is intentionally blank. Robert and Mark must fill it in. The AI cannot be built until these answers are provided.

---

## Document Header Text (verbatim)

> We are building an AI system that will automatically generate survey estimates for every new order that comes into FTF. Before we can build it, the AI needs to learn from you — because you are the people who know how this business works.
>
> Below are the questions we need you to answer. Start with the CRITICAL items first — nothing can be built until those are done. Write your answers in the "Your Answer" column and send back to Prateek.

---

## Section 1 — Recording Sessions (Most Important)

**Priority: CRITICAL**

> Robert and Mark each need to record a screen-share session (using Loom or any recorder) showing how you currently handle a new order from start to finish — opening it, looking up the price, writing the estimate email, and sending it. Narrate everything out loud as you do it. These recordings teach the AI everything it needs to know. We cannot build it without them. Do you need a walkthrough of how to record? Yes / No. When can you do your first recording session?

**Answer needed:** Yes/No on needing walkthrough + date for first recording session.

---

## Section 2 — Survey Names in the FTF System (Critical — AI needs exact names)

**Priority: CRITICAL — row 1**

> When a customer submits a Topographic Survey order in FTF, what exact name appears in the system? The AI's pricing system has it listed as "Topography Survey." Is that the name you see in FTF orders — or is it spelled differently?

**Priority: CRITICAL — row 2**

> When a construction-related job comes in, what service name is used in FTF? The pricing system does not have "Construction Survey" as an option. It has: Building Stake Out, Form Board Survey, Foundation Tie-In, Pad Stake Out. Which one is used, or is it something else?

**Priority: CRITICAL — row 3**

> When a permitting job comes in, what service name is used in FTF? The pricing system does not have "Permitting Survey." Does it go under "Specific Purpose Survey," "Other Services," or something else?

**Priority: HIGH — row 4 (transitional, at bottom of page 1 / top of page 2)**

> The pricing system has a service called "Specific Purpose Survey." Our documents call it "Special Purpose Survey." Which name appears in the actual FTF orders you see?

---

## Section 3 — Flagging Rules (Critical — the AI's decision rules)

**Priority: CRITICAL — row 1 (Competitor / Do-Not-Auto-Quote list)**

> We need a complete list of all company names that should NEVER be auto-quoted by the AI. These are competitor companies, suspicious companies, or anyone where you always stop and check before sending a price. Please list every company name you can think of here, or note them in your recording session (Recording 6).

**Priority: CRITICAL — row 2 (Services NGE does / does not perform)**

> We need a confirmed list of every survey type NGE performs — and every survey type NGE does NOT perform. Anything not on the "we do this" list will be automatically flagged for human review. Please list both — what you do and what you don't do.

**Priority: HIGH — row 3 (Other flag triggers beyond competitors/services)**

> Beyond competitors, construction, and permitting — are there any other situations or order types where you always review manually before sending an estimate? Please list all of them so the AI knows to flag those too.

---

## Section 4 — Specific Services (Need your input before go-live)

**Priority: HIGH — row 1 (Always-human-review services)**

> The FTF pricing system includes these services: ALTA Table A Survey ($1,500) • B-II Title Review ($450) • Wetland Delineation ($300) • Lot Split ($450). Should any of these always go to human review before the AI sends a quote? Or are any of these services NGE does not perform?

**Priority: STANDARD — row 2 (Wetland Delineation)**

> Does NGE perform Wetland Delineation surveys? If yes — does it need a specialist to review before quoting? If no — we will add it to the never-auto-quote list.

**Priority: STANDARD — row 3 (Geographic limitations)**

> Are there any geographic limitations on the orders NGE can accept? For example — are there counties or states where NGE does not operate? If so, the AI should flag orders from those areas immediately instead of quoting them.

---

## Section 5 — Change Order Clause (New requirement — BRD Amendment 001)

**Priority: HIGH — row 1 (Change order clause text)**

> Every estimate the AI generates will now include a change order clause at the bottom. This clause pre-authorises the company to issue a change order if the scope or complexity of a job changes after the estimate is approved. Does the current estimate format already include any change order language — or is this completely new? If there is existing text in use, please share it so we do not duplicate or contradict it.

**Priority: HIGH — row 2 (Customer approval workflow)**

> When a customer approves a survey estimate today — how do they typically do it? Options: • Email reply (e.g. "Please proceed" or "Approved") • Phone call only • They sign something • Other. This matters because the customer's approval of the estimate is also their acceptance of the change order terms. The more formal the approval, the stronger the legal protection.

**Priority: STANDARD — row 3 (Past dispute history)**

> Have customers ever disputed additional charges mid-project — for example, when a job turned out to be more complex than the original estimate? If yes, what were the circumstances? Understanding past friction points will help Ryan write the change order clause so it specifically covers the most common situations.

---

## General Notes (end of document)

> Use this space for anything else you want to add or flag.

*(blank — to be filled by Robert/Mark)*

---

## FTF System Demo — Observed in Recording

**Order observed:** `fieldtofinish.jobs/order/?order=1000284219`

### Order fields visible:
| Field | Value |
|-------|-------|
| Order Rating | 1-Most Easy |
| Needed Date | 06-02-2026 |
| Closing Date | 06-02-2026 |
| Set-up Complete | Yes |
| Ordered By | Law Offices of Jean Cascio, PLLC |
| Contact | Jean Cascio / Jean@CascioLawOffice.com / 9549504606 |
| Order description | Boundary Survey for closing / Quote |
| Property Address | 3721 NE 30TH AVE, LIGHTHOUSE POINT, FL 33064 |
| County | BROWARD COUNT[Y] |
| Property Notes | 26.27706097, -80.08219789 |
| Flood/Hazard Zone | None (dropdown) / FLOOD ZONE (text field) |

### Buttons on order:
- Generate Invoice
- Deliver Invoice
- View Log
- Express Delivery
- Print Documents
- Resend Email
- Move Order to Another Account
- View Company's Profile in Sales

### External Resources panel (right side):
- County GIS Map
- Google Maps
- Street View
- Aerial Map
- Generate — Elev Cert
- Generate — A AO Temp
- Generate — Elev Cert Temp

### Notes tab checkboxes visible:
- Construction/Permitting
- Commercial/ALTA table A
- Qualia Job
- Trueline Job

### Quote PDF observed (frame ~1120):
```
Quote
INVOICE #: 1000284219
FILE #: [blank]
DATE: 05-21-2026
BILL TO:
SERVICE          QUANTITY    COST
Boundary Survey      1       $450.00

Address:
3721 NE 30TH AVE LIGHTHOUSE POINT FL 33064

TOTAL:   $450.00
PAID:    $0.00
BALANCE: $450.00

Notes:
Contact:
(361) 588-4272
```

### Email workflow observed (Outlook, frame ~1130):
Robert's email `robert_e@nexgen[...]` searched for "quote" — showing emails from customers including:
- Jean Cascio ("survey QUOTE needed...")
- Kim Shiela Liedres ("Quote for Survey" — multiple threads)

---

## Google Earth Segment (frames ~960–1080)

The presenter navigated Google Earth showing:
1. A local street-level view (Brevard County area — Space View Park, Indian River visible)
2. Zoomed out to show full Florida peninsula
3. Panned to show South Florida / Miami / Keys / Key West / Islamorada / Marathon
4. Showed northwest Florida coast (Apalachicola, Tallahassee area, Big Bend/Steinhatchee)
5. Showed northeast Florida (Jacksonville, Gainesville, St. Augustine)

**Interpretation:** This segment likely contextualizes geographic flagging rules — illustrating Florida counties NGE serves vs. does not serve, and the Monroe County / Florida Keys geography that triggers special handling. No text annotations or labels were drawn on the map during the recording. This was verbal context only — not captured in the document.

---

## Priority Classification Key (observed in document)

| Badge | Color | Meaning |
|-------|-------|---------|
| CRITICAL | Red | Nothing can be built without this answer |
| HIGH | Orange/Amber | Needed before go-live |
| STANDARD | Blue | Important but can be resolved in iteration |

---

## Open Questions / Ambiguities to Resolve

1. **Service name mappings (Section 2):** ~~All three CRITICAL service name questions are unanswered.~~ **RESOLVED 2026-05-25** — Robert confirmed all four mappings verbally. See "Verbal Answers" section above and I-039 (closed).

2. **Competitor / do-not-quote list (Section 3, row 1):** Still open. Robert confirmed the list exists and will write it up. Tracked as I-040.

3. **NGE service scope (Section 3, row 2):** **RESOLVED 2026-05-25** — Robert confirmed full do/don't-do list verbally. See "Verbal Answers" section above.

4. **Geographic limitations (Section 4, row 3):** **RESOLVED 2026-05-25** — Florida only, all 67 counties. Monroe County flagged (I-034 already built). Northwest FL / Vero Beach manageable. See "Verbal Answers" section above.

5. **ALTA / B-II / Wetland / Lot Split auto-quote decision (Section 4, row 1):** **RESOLVED 2026-05-25** — Robert confirmed: ALTA, B-II Title Review, Wetland Delineation, and Lot Split all require management-level human review before sending.

6. **Wetland Delineation scope (Section 4, row 2):** **RESOLVED 2026-05-25** — NGE does NOT do Wetland Delineation (needs specialist engineer; too complex). Add to never-auto-quote list.

7. **Change order clause existing text (Section 5, row 1):** **RESOLVED 2026-05-25** — Confirmed NO existing change order language in estimates. This is completely new. Ryan to draft (I-042).

8. **Customer approval method (Section 5, row 2):** **RESOLVED 2026-05-25** — Four methods confirmed, most to least common: (1) pay via payment link, (2) email confirmation, (3) FTF portal acceptance, (4) phone call. See "Verbal Answers" section above.

9. **Flood/Hazard Zone logic:** Still open — no rules stated about when EC is required beyond FEMA zone auto-add. Already handled via existing FEMA API logic.

10. **Monroe County / Keys rules:** **RESOLVED 2026-05-25** — Monroe County confirmed for flag + extra charge + limited crew. I-034 already built.

11. **"Specific Purpose Survey" vs "Special Purpose Survey":** **RESOLVED 2026-05-25** — Robert uses "Specific Purpose Survey." Both are interchangeable; use "Specific Purpose Survey" as canonical name.

12. **Recording 6 reference (competitor list):** Still open. Robert confirmed list exists. Tracked as I-040.

13. **Building Stakeout service status:** Ambiguous — Robert says NGE is "dabbling" in it again. Treat as flag-for-human-review until formally confirmed back in service. Tracked as I-041.

14. **AI pipeline design (suggest vs. auto-send):** **NEW FINDING 2026-05-25** — Robert said he ALWAYS personally reviews every estimate before sending. Pipeline must be configured as suggest-then-approve for ALL orders. Tracked as I-043.

---

## Config Values Visible / Inferable

| Item | Value | Source |
|------|-------|--------|
| ALTA Table A Survey price | $1,500 | Section 4 document text |
| B-II Title Review price | $450 | Section 4 document text |
| Wetland Delineation price | $300 | Section 4 document text |
| Lot Split price | $450 | Section 4 document text |
| Boundary Survey sample quote | $450 | Live FTF demo, frame ~1120 |
| FTF system URL | fieldtofinish.jobs | Live demo |
| FEMA Flood Map Service | Linked from FTF External Resources panel | Live demo |

---

*FTF Agentic AI OS | Robert & Mark | Confidential*
*Extracted by AI frame analysis | May 2026*
