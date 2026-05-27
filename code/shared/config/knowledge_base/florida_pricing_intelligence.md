# Florida Land Surveying — Pricing Intelligence
# Researched 2026-05-27 | Sources: apex survey, promatcher, firstchoicesurveying, angi
# Purpose: AI pricing reference for NexGen estimate generation

## Market Price Ranges by Service Type (2026)

| Service | Low | Typical | High | Notes |
|---|---|---|---|---|
| Boundary Survey (residential) | $400 | $500–$2,000 | $3,000+ | Platted lot starts ~$425–$500 |
| Topographic Survey | $800 | $1,200–$3,500 | $6,500+ | Residential 1 ac; per-acre for larger |
| ALTA Table A Survey | $2,500 | $3,000–$6,000 | $10,000+ | Table A items add $500–$2,000+ |
| Elevation Certificate | $300 | $400–$700 | $900 | Standalone; $175 with survey order |
| Form Board / Foundation Survey | $400 | $400–$900 | $1,200 | Same-day delivery; required pre-pour |
| Final Survey / As-Built | $500 | $500–$1,500 | $2,500 | Required for CO |
| Update Survey / Recertification | $300 | $350–$700 | $1,000 | 40-60% less than new survey |
| Boundary Survey baseline (ProMatcher FL avg) | — | $648 | — | Range $429–$868, up to 0.5 ac |

---

## County / Regional Pricing Modifiers

| County | Region | Modifier | Boundary Range | ALTA Range | Notes |
|---|---|---|---|---|---|
| Miami-Dade | South FL | +15–25% | $600–$2,500 | $3,000–$7,000+ | Dense records, flood zone ubiquity |
| Broward | South FL | +15–20% | $575–$2,200 | $3,000–$6,500 | Similar to Miami-Dade |
| Palm Beach | South FL | +10–20% | $550–$2,500 | $3,000–$7,000+ | Large lots in western areas |
| Monroe (Keys) | South FL | +20–30% est. | $700–$3,000+ | $3,500–$8,000+ | Island access, tidal, CCCL |
| Hillsborough | Central FL | +5–15% | $500–$2,000 | $2,500–$6,000 | Tampa; active construction |
| Orange | Central FL | +5–15% | $500–$2,000 | $2,500–$6,000 | Orlando; strong residential |
| Pinellas | Central FL | +10–15% | $550–$2,000 | $2,500–$5,500 | Waterfront complexity |
| Duval | North FL | Baseline | $450–$1,800 | $2,200–$5,000 | Jacksonville baseline |
| Lee | SW FL | +5–10% | $500–$1,900 | $2,500–$5,500 | Post-Ian rebuild demand |
| Collier | SW FL | +10–15% | $550–$2,000 | $2,500–$5,500 | Naples premium |
| Polk | Central FL | Baseline | $450–$1,700 | $2,000–$4,500 | Lower density; rural common |
| Panhandle | NW FL | At or below | $400–$1,600 | $2,000–$4,500 | Lowest cost region |

---

## Dynamic Complexity Factors (I-065)

Ryan (2026-05-26): "Same half-acre with pool, 30 walls, shed, 2 driveways = $700.
Same half-acre plain house = $350. Far from crew = charge more for travel."

### Property / Lot Factors
| Factor | Typical Upcharge |
|---|---|
| Swimming pool | +$100–$200 |
| Each additional structure (shed, guest house) | +$75–$150 per structure |
| Back patio (large, complex) | +$75–$125 |
| Per additional structure improvement beyond first | +$100–$300 |
| Number of walls / corners (30+ vs. 4 simple) | +$50–$150 per 10 extra corners |
| Multiple / looping driveways (vs. single straight) | +$100–$200 |
| Irregular lot shape / metes-and-bounds (vs. platted) | +$100–$400 |
| Missing or destroyed monuments | +$100–$400 per corner |
| Flood zone location (AE/VE) | +$50–$150 research time |

### Site Access / Terrain
| Factor | Typical Upcharge |
|---|---|
| Dense vegetation, wetlands, swamp | +20–40% fieldwork |
| Remote / rural property (>30 mi from crew base) | +10–20% travel |
| Very remote (top of state, no nearby crew) | +15–30% travel |
| Gated or restricted access | scheduling delay; quote manually |

### Service-Level Factors
| Factor | Typical Upcharge |
|---|---|
| Rush turnaround (24–48 hr) | +15–50% |
| Elevation certificate ordered standalone | +$100–$150 vs. bundled |
| Topographic contour interval <2 ft | +15–25% |
| Peak season (February–May) | extended backlog; rush premium higher |

### Research / Legal Complexity
| Factor | Typical Upcharge |
|---|---|
| Older metes-and-bounds deed (pre-1960s) | +$150–$500 |
| Conflicting descriptions or gap/overlap | +$200–$600 |
| Easement research (utility, access, drainage) | +$100–$300 |
| Monroe County (non-standard pricing) | flag for human review |

---

## Important Pricing Rules for AI Agent

1. **No association fee schedule** — FSMS (FL Surveying Society) cannot publish price lists under FL antitrust law. All pricing is market-driven.

2. **County matters** — South FL (Palm Beach, Broward, Miami-Dade) orders cost 10-25% more than baseline; adjust estimate accordingly.

3. **Elevation certificate** — always auto-add $225 when is_flood_zone=True (AE zone). VE zone → flag for human; elevation cert still likely needed.

4. **ALTA surveys** — always flag for human review. Too variable for auto-quote.

5. **Distance modifier** — if property is in remote area (panhandle, very rural) with no nearby crew, apply travel upcharge. Use county + lat/lng to estimate distance.

6. **Reference historical invoices** — when similar jobs have been done, AI should reference past invoice amounts from the same county + service type to calibrate estimate.

---

## NexGen's Current Flat Rates (FTF Pricing API — staging)

| Service | Individual | B2B |
|---|---|---|
| Boundary Survey | $350 | TBD |
| Elevation Certificate | $225 | TBD |
| Form Board Survey | $225 | TBD |
| Final Survey | $300 | TBD |
| Topography Survey | $225 | TBD |
| Update Survey | $350 | TBD |

Note: NexGen's FTF flat rates are below market average. Dynamic pricing factors above allow the AI to adjust these upward for complex jobs as Robert/Ryan intended.
