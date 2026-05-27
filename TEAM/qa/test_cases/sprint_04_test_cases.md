# Sprint 4 — Test Cases: Agent 6 Writer + Change Order Clause

> Written by Senior QA before dev starts. All cases must pass before Sprint 4 is marked ✅ Complete.
> Reference: `sprints/sprint_04_writer.md`

---

## Unit Tests (`code/sprint_04_writer/tests/test_writer.py`)

| ID | Scenario | Input | Expected Output | Pass? |
|----|----------|-------|-----------------|-------|
| UT-04-01 | Individual customer → warm/friendly tone | `customer_type="individual"`, cleared order from Human Gate | LLM prompt contains tone instruction `"warm"` or `"friendly"`; draft produced | ✅ |
| UT-04-02 | B2B customer → concise/professional tone | `customer_type="b2b"`, cleared order | LLM prompt contains tone instruction `"professional"` or `"concise"` | ✅ |
| UT-04-03 | Change order clause injected into LLM prompt | Any cleared order | Full text of `change_order_clause.txt` present in LLM system prompt | ✅ |
| UT-04-04 | Change order clause is LAST section in draft | Generated draft estimate | Clause text appears at end of draft — no content after clause | ✅ |
| UT-04-05 | Clause text unmodified — exact file match | Generated draft | `draft[-len(clause):]` == `clause` content exactly | ✅ |
| UT-04-06 | Customer name in estimate matches FTF order | `customer_name="John Doe"` in order | Draft contains `"John Doe"` — not abbreviated, not altered | ✅ |
| UT-04-07 | Property address in estimate matches FTF order | `property_address="123 Main St, Miami FL 33101"` | Draft contains exact property address | ✅ |
| UT-04-08 | Price in estimate matches pricing engine output | `pricing["amount"] == 525` | Draft contains `"$525"` or `"525.00"` — exact match | ✅ |
| UT-04-09 | `write_estimate(correction_note=)` accepted for Reviewer retry | `correction_note="Price was incorrect, use $450"` | Correction note appended to LLM prompt on retry | ✅ |
| UT-04-10 | Zero amount raises `AgentError` | `pricing["amount"] == 0` | `AgentError` raised — $0 estimate NEVER drafted | ✅ |
| UT-04-11 | DB status updated to `"written"` after draft saved | Successful draft generation | `processed_orders.status = "written"` | ✅ |
| UT-04-12 | `draft_estimate` column populated in DB | Successful draft generation | `processed_orders.draft_estimate` contains full email text | ✅ |
| UT-04-13 | Clause loaded from file via `Path(...).read_text()` | `change_order_clause.txt` present | Clause loaded fresh per call — not hardcoded string | ✅ |

---

## Integration Tests (Staging — Sprint 10)

| ID | Scenario | How to Run | Expected Result | Pass? |
|----|----------|-----------|-----------------|-------|
| IT-04-01 | Individual order — warm tone draft produced | Submit individual `Boundary Survey` order; run full pipeline to agent 6 | Draft email in DB is warm/friendly in tone; clause present as last section | ✅ |
| IT-04-02 | B2B order — professional tone draft produced | Submit B2B order; run full pipeline | Draft is concise/professional; no casual language | ✅ |
| IT-04-03 | Reviewer retry loop — correction applied | Agent 7 sends correction back to Agent 6 | Second draft fixes the flagged issue; change order clause still present | ✅ |
| IT-04-04 | Ryan reads sample estimate on staging | Generate staging estimate; share with Ryan | Ryan confirms: professional, correct, clause visible | ✅ |

---

## Edge Cases

| ID | Scenario | Expected Behavior | Pass? |
|----|----------|-------------------|-------|
| EC-04-01 | `change_order_clause.txt` file missing | `AgentError` raised — agent does not produce a clauseless estimate | ✅ |
| EC-04-02 | LLM returns draft without clause appended | Draft fails Reviewer check 1 (EC-04-02 → triggers UT-04-09 retry path) | ✅ |
| EC-04-03 | Order in wrong status (not `cleared` / `approved`) when writer runs | `AgentError` raised — writer only acts on correct status | ✅ |
| EC-04-04 | Customer name has special characters or unicode | Draft produced correctly; name not mangled or escaped | ✅ |
| EC-04-05 | Very long property address (multi-parcel) | Draft contains full address — not truncated | ✅ |
| EC-04-06 | LLM call fails (Anthropic API error) | `AgentError` raised; DB status NOT advanced; no partial draft saved | ✅ |

---

## Acceptance Criteria (All must be green to close Sprint 4)

- [ ] UT-04-01 through UT-04-13 all pass
- [ ] Change order clause present as LAST section in EVERY draft estimate
- [ ] Clause text unmodified — exact string match against `change_order_clause.txt`
- [ ] Individual tone (warm/friendly) and B2B tone (professional/concise) are distinct and correct
- [ ] Customer name exact match — no abbreviation
- [ ] Property address exact match
- [ ] Price exact match to pricing engine output
- [ ] `$0` amount raises `AgentError` — never sends zero-dollar estimate
- [ ] `correction_note=` parameter works for Reviewer retry loop
- [ ] Prateek (CTO) sign-off on code and sample outputs
- [ ] Ryan reviews sample estimate (1 individual, 1 B2B) and approves tone and clause wording before Sprint 6 go-live (I-043)

---

## Notes

- Integration tests (IT-*) run during Sprint 10 (full staging). Unit tests (UT-*) run during Sprint 4.
- Ryan must review `change_order_clause.txt` text before Sprint 6 go-live (I-043) — adjustments are text file edits, no code changes.
- Sprint 4 completed 2026-05-26 — 13 unit tests all passing; full suite 125/125.
- Prompts stored in `shared/config/prompts/estimate_writer.txt` — not sprint-local.
