# Sprint 10 — Internal Staging Test Report

**Date:** 2026-05-27  
**Run by:** Internal team (Prateek + AI agents)  
**Result:** ✅ PASS — 29/30 checks passed, 1 warnings

---

## 1. Live Connection Checks

| Check | Status | Detail |
|-------|--------|--------|
| FTF /health | ✅ PASS | 200 OK |
| FTF /orders (5-order sample) | ✅ PASS | 5 orders, total in system: see logs |
| Claude (claude-haiku-4-5-20251001) | ✅ PASS | OK |
| PostgreSQL (processed_orders) | ✅ PASS | table accessible |
| FEMA flood zone API | ⚠️ WARN | FEMA API unavailable |

**4/5 passed**

## 2. Full pytest Suite

| Check | Status | Detail |
|-------|--------|--------|
| All sprint tests | ✅ PASS | 239 passed in 3.32s |

**1/1 passed**

## 3. Order Type Classification (12 types)

| Check | Status | Detail |
|-------|--------|--------|
| Standard boundary survey | ✅ PASS | expected=auto got=auto |
| Elevation cert ($225 flat) | ✅ PASS | expected=auto got=auto |
| Mortgage survey | ✅ PASS | expected=auto got=auto |
| Update survey | ✅ PASS | expected=auto got=auto |
| Final survey — post-construction | ✅ PASS | expected=auto got=auto |
| ALTA — always flag | ✅ PASS | expected=flag got=flag |
| Building Stake Out — always flag | ✅ PASS | expected=flag got=flag |
| Topography — never auto-quote | ✅ PASS | expected=flag got=flag |
| Lot Split — county approval needed | ✅ PASS | expected=flag got=flag |
| Wetland — FDEP jurisdiction | ✅ PASS | expected=flag got=flag |
| Specific Purpose — scope undefined | ✅ PASS | expected=flag got=flag |
| Order from competitor domain | ✅ PASS | expected=competitor got=competitor |

**12/12 passed**

## 4. AR Escalation Logic

| Check | Status | Detail |
|-------|--------|--------|
| Day 45 — no alert expected | ✅ PASS | days=45 level=1 -> 60d=False 90d=False |
| Day 65 — 60d alert to Jessica | ✅ PASS | days=65 level=1 -> 60d=True 90d=False |
| Day 95, level=1 — both 60d and 90d fire (90d processed first) | ✅ PASS | days=95 level=1 -> 60d=True 90d=True |
| Day 95, level=2 — still escalates to level 3 | ✅ PASS | days=95 level=2 -> 60d=False 90d=True |
| Day 65, level=2 — already alerted, skip | ✅ PASS | days=65 level=2 -> 60d=False 90d=False |
| Day 110, level=3 — already escalated, skip | ✅ PASS | days=110 level=3 -> 60d=False 90d=False |

**6/6 passed**

## 5. Statement Generation

| Check | Status | Detail |
|-------|--------|--------|
| Group by billing email | ✅ PASS | 2 clients: ['billing@acme-title.com', 'accounts@lawfirm-test.com'] |
| Excel generated — billing@acme-title.com | ✅ PASS | 5954 bytes |
| PDF generated — billing@acme-title.com | ✅ PASS | 2349 bytes |
| Excel generated — accounts@lawfirm-test.com | ✅ PASS | 5814 bytes |
| PDF generated — accounts@lawfirm-test.com | ✅ PASS | 2119 bytes |

**5/5 passed**

## 6. Claude API Cost Benchmark

| Check | Status | Detail |
|-------|--------|--------|
| Cost benchmark report written | ✅ PASS | $0.00/month est. — C:\Users\Prateek Chandra\OneDrive - NexGen Enterprises\Claude |

**1/1 passed**

---

## Internal Sign-Off

| Role | Person | Status |
|------|--------|--------|
| CTO | Prateek | ✅ Approved |
| AR Lead | Jessica | 🔲 Sprint 10 staging review |
| Oversight | Wyatt | 🔲 Sprint 10 staging review |
| Operations | Robert / Mark | 🔲 Sprint 10 staging review |
| Decision Maker | Ryan | 🔲 Cost approval + GO/NO-GO |

*External stakeholder reviews scheduled for Sprint 10 staging session.*