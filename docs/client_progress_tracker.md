# FTF Agentic AI OS — Project Progress Tracker

**Client:** Norman G. Ehlers (NGE) — Field to Finish
**Project:** Agentic AI Operating System
**Last Updated:** 2026-05-28
**Overall Status:** 🔄 Sprint 11 In Progress — production credential swap needed to go live

---

## Sprint Overview

| Sprint | What Gets Built | Owner | Status | Completion Date |
|--------|----------------|-------|--------|----------------|
| Sprint 0 | Foundation — GitHub repo, database, API connections, all infrastructure | Prateek | ✅ Complete | 2026-05-21 |
| Sprint 1 | Order Detection — AI monitors FTF every 60 min for new survey orders | Prateek | ✅ Complete | 2026-05-22 |
| Sprint 2 | Smart Classification — AI reads order type, customer tier, flood zone | Prateek | ✅ Complete | 2026-05-25 |
| Sprint 3 | Flag Detection & Human Gate — 12 triggers, hourly batch digest to Robert | Prateek | ✅ Complete | 2026-05-25 |
| Sprint 4 | Estimate Writer — AI writes personalized estimate + change order clause | Prateek | ✅ Complete | 2026-05-26 |
| Sprint 5 | Quality Control — AI reviews its own estimate, self-corrects up to 3 times | Prateek | ✅ Complete | 2026-05-26 |
| Sprint 6 ⭐ | **MILESTONE — First full estimate loop (Sender + Reporter) + staging demo** | Prateek + Ryan | ✅ Complete | 2026-05-26 |
| Sprint 7 | AR Follow-Up Loop — internal Teams alerts at Day 60 / Day 90 overdue | Prateek + Jessica | ✅ Complete | 2026-05-27 |
| Sprint 8 | Monthly Statement Loop — Excel + PDF B2B statements on 1st of every month | Prateek + Wyatt | ✅ Complete | 2026-05-27 |
| Sprint 9 | Memory Loop + AI Business Analyst — nightly learning cycle, Anthropic-powered analysis | Prateek | ✅ Complete | 2026-05-27 |
| Sprint 10 ⭐ | **MILESTONE — All 3 loops on staging, full system demo — Ryan issued GO** | All stakeholders | ✅ Complete | 2026-05-27 |
| Sprint 11 ⭐ | Limited Production — estimate loop live, Robert/Mark monitor first 5 estimates | Prateek + Robert | 🔄 In Progress | TBD |
| Sprint 12 ⭐ | **Full Production — all 3 loops live, AI runs 24/7 autonomously** | Ryan sign-off | 🔲 Not Started | — |

---

## Actions Required from Client Team

| Priority | Action Needed | Who | Needed Before | Status |
|----------|--------------|-----|---------------|--------|
| 🔴 CRITICAL | Provide production FTF API key (not staging) | FTF Developer / Ryan | Sprint 11 go-live | ⏳ Pending |
| 🔴 CRITICAL | Provide production FTF Books credentials (email + password) | FTF Developer / Ryan | Sprint 11 go-live | ⏳ Pending |
| 🔴 CRITICAL | Confirm production FTF API base URL | FTF Developer | Sprint 11 go-live | ⏳ Pending |
| 🟡 HIGH | Robert/Mark: monitor and approve first 5 real estimates | Robert / Mark | Sprint 11 observation | ⏳ Pending |
| 🟡 HIGH | Confirm full service type list from FTF order form | Robert | Sprint 11 (I-045) | ⏳ Pending |
| 🟡 HIGH | Confirm multi-service child order handling in FTF API | FTF Developer | Sprint 11 (I-073) | ⏳ Pending |
| 🟢 LOW | Confirm Table Survey canonical mapping | Robert | Sprint 11 (I-071) | ⏳ Pending |
| 🟢 LOW | Provide chat widget for website order conversion | FTF Developer / Prateek | Sprint 12 (I-062) | ⏳ Future |

---

## Milestone Sign-Off Required

| Milestone | What Ryan Approves | Status |
|-----------|-------------------|--------|
| Sprint 6 — Full estimate loop | First AI-generated estimate on staging — tone and format correct | ✅ APPROVED (Ryan demo, 2026-05-26) |
| Sprint 10 — Full system demo | Live demo of all 3 loops on staging; monthly AI cost approved | ✅ APPROVED (Ryan, 2026-05-27) — issued GO for Sprint 11 |
| Sprint 11 — Production go-live | First 5 real estimates reviewed by Robert/Mark → report to Ryan | 🔲 Pending (awaiting production credentials) |
| Sprint 12 — Full handover | All 3 loops running autonomously for 30 days — final Phase 1 sign-off | 🔲 Pending |

---

## Status Key

| Icon | Meaning |
|------|--------|
| 🔲 | Not Started |
| 🔄 | In Progress |
| ✅ | Complete |
| 🚫 | Blocked |
| ⚠️ | Needs Review |
| ⏳ | Pending |
| ⭐ | Milestone sprint |
