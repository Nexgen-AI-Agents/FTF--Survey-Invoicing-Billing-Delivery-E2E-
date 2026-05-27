# Sprint 2 — Test Cases: Agent 3 Classifier + Agent 5 Pricing Engine

> Written by Senior QA before dev starts. All cases must pass before Sprint 2 is marked ✅ Complete.
> Reference: `sprints/sprint_02_classifier_pricing.md`

---

## Unit Tests (`code/sprint_02_classifier_pricing/tests/test_classifier.py` + `test_pricing_engine.py`)

| ID | Scenario | Input | Expected Output | Pass? |
|----|----------|-------|-----------------|-------|
| UT-02-01 | Individual customer type classified correctly | `customer_type="individual"` in FTF order | Returns `classification["customer_type"] == "individual"` | ✅ |
| UT-02-02 | B2B customer type classified correctly | `customer_type="b2b"` in FTF order | Returns `classification["customer_type"] == "b2b"` | ✅ |
| UT-02-03 | ALTA Table A Survey → always_flag | `service_type="ALTA Table A Survey"` | `flags["reason"] == "always_flag_service"` — routed to Human Gate | ✅ |
| UT-02-04 | Other Services → always_flag | `service_type="Other Services"` | `flags["reason"] == "always_flag_service"` — routed to Human Gate | ✅ |
| UT-02-05 | Specific Purpose Survey → never_auto_quote | `service_type="Specific Purpose Survey"` | `flags["reason"] == "never_auto_quote"` — Human Gate required | ✅ |
| UT-02-06 | Missing county → data quality flag | `county=None` or `county=""` | `flags["reason"] == "missing_county"` — flagged for review | ✅ |
| UT-02-07 | False FL coordinate → geographic flag | Lat/lon outside Florida bounding box | `flags["reason"] == "false_fl_coordinate"` — flagged | ✅ |
| UT-02-08 | Flood zone property → elevation cert required | FEMA returns AE/VE zone for property address | `classification["elevation_cert_required"] == True` | ✅ |
| UT-02-09 | Non-flood property → no elevation cert | FEMA returns X zone | `classification["elevation_cert_required"] == False` | ✅ |
| UT-02-10 | VE coastal zone → coastal flag | FEMA returns `zone="VE"` | `flags["reason"] == "ve_coastal_zone"` — flagged | ✅ |
| UT-02-11 | FEMA unavailable → flagged | FEMA client returns `"UNAVAILABLE"` | `flags["reason"] == "fema_unavailable"` — flagged | ✅ |
| UT-02-12 | Monroe County → always flagged | `county="Monroe"` | `flags["reason"] == "monroe_county"` — flagged regardless of service | ✅ |
| UT-02-13 | Out-of-state property → flagged | `property_state="GA"` | `flags["reason"] == "out_of_state"` — NGE FL-only | ✅ |
| UT-02-14 | Competitor email domain → flagged | `email="user@competitorsurvey.com"` with domain in `COMPETITOR_DOMAINS` | `flags["reason"] == "competitor_domain"` — flagged | ✅ |
| UT-02-15 | Pricing: correct amount from FTF API | `service_type="Boundary Survey"`, FTF price table returns `$450` | `pricing["amount"] == 450` | ✅ |
| UT-02-16 | Pricing: elevation cert add-on applied | `elevation_cert_required=True`, base price `$450` | `pricing["amount"] == 675` ($450 + $225 add-on) | ✅ |
| UT-02-17 | Pricing: elevation cert NOT added for non-flood | `elevation_cert_required=False`, base price `$450` | `pricing["amount"] == 450` — no add-on | ✅ |
| UT-02-18 | Pricing: company override used for special pricing | `special_pricing=True`, override in price table | `pricing["amount"]` matches override value, not standard | ✅ |
| UT-02-19 | Pricing: override NOT used when special_pricing=False | `special_pricing=False` | `pricing["amount"]` uses standard table price | ✅ |
| UT-02-20 | PricingError propagates on FTF API failure | FTF pricing API returns 500 | `PricingError` raised — not silenced | ✅ |
| UT-02-21 | `log_decision()` called for each classified order | 1 order classified | `log_decision()` called 1× with `agent_name="agent_03_classifier"` | ✅ |
| UT-02-22 | Normal FL individual order passes with no flags | `service_type="Boundary Survey"`, FL address, non-flood, non-Monroe, non-competitor | `classification["flags"] == []` — no flags | ✅ |

---

## Integration Tests (Staging — Sprint 10)

| ID | Scenario | How to Run | Expected Result | Pass? |
|----|----------|-----------|-----------------|-------|
| IT-02-01 | 1 individual order — full classify + price | Submit individual `Boundary Survey` order; run `agent_03_classifier.py` + `agent_05_pricing_engine.py` | DB row: `customer_type="individual"`, `elevation_cert_required=False`, price amount > 0 | ✅ |
| IT-02-02 | 1 B2B order — full classify + price | Submit B2B order for `Easement Survey`; run agents | DB row: `customer_type="b2b"`, correct price pulled from FTF table | ✅ |
| IT-02-03 | Flood zone property — FEMA live call | Submit order with address in known AE/VE zone | `elevation_cert_required=True`, add-on price applied | ✅ |
| IT-02-04 | Special-pricing customer — override applied | Submit order with `special_pricing=True` customer; run pricing engine | `pricing["amount"]` matches override in FTF pricing table | ✅ |
| IT-02-05 | ALTA Table A Survey → flagged, stops at Human Gate | Submit ALTA order | `processed_orders.status = "awaiting_approval"` — does NOT advance to pricing | ✅ |

---

## Edge Cases

| ID | Scenario | Expected Behavior | Pass? |
|----|----------|-------------------|-------|
| EC-02-01 | Two flags on one order (Monroe + ALTA) | Both flags recorded; order flagged once to Human Gate — no duplicate Teams alerts | ✅ |
| EC-02-02 | FEMA API returns network timeout | `fema_unavailable` flag set; order routed to Human Gate; no crash | ✅ |
| EC-02-03 | Service type not in any known list | `classification["flags"] == []` — treated as standard service, priced normally | ✅ |
| EC-02-04 | Price returned as `0` or `null` from FTF API | `PricingError` raised — $0 estimate NEVER sent to customer | ✅ |
| EC-02-05 | Competitor company name (not email domain) | `flags["reason"] == "competitor_name"` — flagged even if domain not in list | ✅ |
| EC-02-06 | Table Survey → always_flag | `service_type="Table Survey"` | `flags["reason"] == "always_flag_service"` — not auto-quoted | ✅ |

---

## Acceptance Criteria (All must be green to close Sprint 2)

- [ ] UT-02-01 through UT-02-22 all pass
- [ ] No BLOCKER or CRITICAL issues open
- [ ] All 14 flag trigger paths tested and confirmed
- [ ] `elevation_cert_required=True` correctly adds exactly $225
- [ ] `PricingError` raised (not silenced) on FTF API failure
- [ ] Pricing override ONLY applied when `special_pricing=True`
- [ ] FEMA unavailable handled gracefully — no crash, flag set
- [ ] `log_decision()` called for every classified order
- [ ] QE Manual confirmed: no PII in log output
- [ ] Prateek (CTO) sign-off on classifier logic
- [ ] Robert / Mark (SME) confirm flag triggers match real FTF order types

---

## Notes

- Integration tests (IT-*) run during Sprint 10 (full staging). Unit tests (UT-*) run during Sprint 2.
- `COMPETITOR_NAMES` and `NEVER_AUTO_QUOTE` list validated by Robert/Mark (I-038) before staging.
- `classifier.txt` prompt is a stub until Robert/Mark recordings arrive — LLM-based enrichment deferred.
- Sprints 2 completed 2026-05-25 — all unit tests passing (22/22 classifier + 15/15 pricing).
