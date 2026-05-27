# Sprint 10 — Test Cases: Full Staging E2E Test + Cost Benchmark

> Written by Senior QA before dev starts. All cases must pass before Sprint 10 is marked ✅ Complete.
> Reference: `sprints/sprint_10_staging_test.md`

---

## Unit Tests (Staging Validator — `scripts/run_sprint10_internal.py`)

| ID | Scenario | Input | Expected Output | Pass? |
|----|----------|-------|-----------------|-------|
| UT-10-01 | All 17 agents importable without errors | Run `run_sprint10_internal.py` Section 1 | All agent modules import cleanly; no `ImportError` or `ModuleNotFoundError` | ✅ |
| UT-10-02 | Individual Boundary Survey — classified and priced | Submit test individual order | `customer_type="individual"`, `price > 0`, no flags | ✅ |
| UT-10-03 | B2B Easement Survey — classified and priced | Submit test B2B order | `customer_type="b2b"`, correct price, no flags | ✅ |
| UT-10-04 | ALTA Table A Survey → flagged, halted at Human Gate | Submit ALTA order | `status="awaiting_approval"`; Teams alert payload verified | ✅ |
| UT-10-05 | Other Services → flagged, halted | Submit Other Services order | `status="awaiting_approval"` | ✅ |
| UT-10-06 | Monroe County order → flagged | Submit order with `county="Monroe"` | `flags` contains `"monroe_county"`; `status="awaiting_approval"` | ✅ |
| UT-10-07 | Out-of-state property → flagged | Submit order with `property_state="TX"` | `flags` contains `"out_of_state"`; `status="awaiting_approval"` | ✅ |
| UT-10-08 | Competitor domain → flagged | Submit order with `email` containing known competitor domain | `flags` contains `"competitor_domain"` | ✅ |
| UT-10-09 | Flood zone property → elevation cert add-on applied | Submit order in AE/VE zone on staging | `elevation_cert_required=True`; `price += $225` | ✅ |
| UT-10-10 | FEMA unavailable → flagged gracefully | FEMA strategy 1 fails; strategy 2 fails; strategy 3 (ArcGIS) succeeds | Zone returned correctly from ArcGIS; no crash | ✅ |
| UT-10-11 | Estimate Loop: full pipeline completes within 60 min | Clean individual order submitted to staging | `status="sent"` within 60 min; estimate in test inbox | ✅ |
| UT-10-12 | AR Loop: Day 60 alert fires on staging test invoice | Test invoice with `days_overdue=65` | Teams alert sent to Jessica; `escalation_level=2` | ✅ |
| UT-10-13 | AR Loop: Day 90 alert fires to all stakeholders | Test invoice with `days_overdue=92` | Teams alert sent to all 5 stakeholders | ✅ |
| UT-10-14 | Statement Loop: statement generated on staging "1st" | Override date to 1st; run generator | Excel + PDF files created; reviewed and sent via SMTP | ✅ |
| UT-10-15 | Memory loop: nightly log written after run | Run orchestrator + memory manager | `docs/memory/YYYY-MM-DD.md` written | ✅ |
| UT-10-16 | No cross-loop interference — DB isolation | Run all 3 loops simultaneously | No `processed_orders` row touched by AR or Statement loop; no `ar_reminders` row touched by Estimate loop | ✅ |

---

## Integration Tests (Full Staging — Sprint 10 is the integration sprint)

| ID | Scenario | How to Run | Expected Result | Pass? |
|----|----------|-----------|-----------------|-------|
| IT-10-01 | 10+ distinct order types processed — all correct | Run `run_sprint10_internal.py` end-to-end | 29/30 checks pass (1 WARN allowed for FEMA SSL — network-dependent) | ✅ |
| IT-10-02 | `benchmark_credits.py` runs — monthly cost calculated | Run `scripts/benchmark_credits.py` | `docs/benchmark_credits_2026-05-27.md` generated with per-loop cost breakdown | ✅ |
| IT-10-03 | Cost report presented to Ryan — Ryan approves | Review `benchmark_credits_2026-05-27.md` | Ryan signs off on monthly AI cost estimate; GO for Sprint 11 | ✅ |
| IT-10-04 | Full system demo — all stakeholders attend | Demo all 3 loops live on staging | Ryan, Robert/Mark, Jessica, Wyatt all confirm behavior is correct | ✅ |
| IT-10-05 | FEMA 3-strategy fallback validated | Run FEMA check when primary endpoint returns TLS error | Strategy 3 (ArcGIS Online) returns correct zone; no crash | ✅ |

---

## Edge Cases

| ID | Scenario | Expected Behavior | Pass? |
|----|----------|-------------------|-------|
| EC-10-01 | Staging run is non-destructive — no live DB writes | `run_sprint10_internal.py` run mode | No rows written to production DB; no real Teams messages sent; no real emails | ✅ |
| EC-10-02 | FEMA primary endpoint SSL failure (Python 3.14 TLS) | `UNEXPECTED_EOF_WHILE_READING` on `hazards.fema.gov` | Strategy 2 (no-verify) or Strategy 3 (ArcGIS) used; WARN logged but not fatal | ✅ |
| EC-10-03 | Cost benchmark runs even if some agents had no activity | Some loops have 0 cycles during benchmark period | Report still generated; zero-activity loops shown as $0.00 | ✅ |
| EC-10-04 | NEVER_AUTO_QUOTE service type tested on staging | Submit `Lot Split` or `Wetland Delineation` order | Flagged and halted at Human Gate — never priced or sent | ✅ |
| EC-10-05 | B-II Title Review → always_flag on staging | Submit `B-II Title Review` order | Flagged; `status="awaiting_approval"` | ✅ |
| EC-10-06 | Building Stake Out → always_flag on staging | Submit `Building Stake Out` order | Flagged; `status="awaiting_approval"` | ✅ |

---

## Acceptance Criteria (All must be green to close Sprint 10)

- [ ] 29+ out of 30 staging checks pass (29/30 threshold)
- [ ] All 3 loops (Estimate, AR, Statement) run simultaneously with no interference
- [ ] FEMA 3-strategy fallback working — no hard failures on SSL errors
- [ ] `benchmark_credits.py` generates cost report successfully
- [ ] Ryan approves monthly AI cost — GO/NO-GO: GO for Sprint 11
- [ ] Estimate delivers within 60 min on staging
- [ ] AR alert tiers (Day 60 → Jessica; Day 90 → all 5) confirmed by Jessica on staging
- [ ] Monthly statement format confirmed by Wyatt on staging
- [ ] All ALWAYS_FLAG_SERVICES flagged correctly (ALTA, Other Services, B-II Title Review, Building Stake Out, Table Survey)
- [ ] All NEVER_AUTO_QUOTE services flagged correctly (Specific Purpose Survey, Lot Split, Wetland Delineation, Topography Survey)
- [ ] Full stakeholder demo completed: Ryan, Robert/Mark, Jessica, Wyatt all sign off

---

## Notes

- Sprint 10 IS the integration sprint — IT-* and UT-* both run here.
- Staging test run as non-destructive validator: no live DB writes, no Teams messages, no emails.
- Sprint 10 completed 2026-05-27 — 29/30 PASS, 1 WARN (FEMA SSL); Ryan issued GO for Sprint 11.
- FEMA rewrite: 3-strategy fallback (primary SSL → primary no-verify → ArcGIS Online alternate) added to handle Python 3.14 TLS tightening.
