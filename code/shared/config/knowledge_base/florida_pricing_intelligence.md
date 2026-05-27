# Florida Land Surveying — Pricing Intelligence
# Updated 2026-05-27 with PRODUCTION DATA: 23,353 NexGen invoices (May 2025–May 2026)
# Source: nexgen_ftf_db prod DB — actual prices NexGen charged, not market estimates

## ACTUAL NexGen Prices by Service Type (production 1-year data)

| Service | Orders | Avg Actual | Min | Max | Catalogue | Notes |
|---|---|---|---|---|---|---|
| Land Survey Only (= Boundary Survey) | 13,260 | $616 | $0.01 | $35,000 | $350 | Most common service (57% of volume) |
| Land Survey and Elevation (bundle) | 5,654 | $400 | $0.01 | $12,500 | N/A | 49% billed <$300 (partial/EC portion) |
| Boundary Survey | 992 | $567 | $50 | $10,000 | $350 | Explicit catalogue name |
| Re-Survey / Update Survey | 406 | $397 | $0.01 | $2,800 | $250 | Alias for Update Survey |
| Elevation Certificate | 365 | $271 | $0.01 | $1,500 | $225 | |
| ALTA Table A Survey | 16 | $5,075 | $1,500 | $12,500 | $1,500 | Always custom-priced |
| Topography Survey | 61 | $484 | $75 | $1,800 | $225 | |
| Spot Survey (New client) | 106 | $589 | $350 | $2,500 | N/A | = Foundation Tie-In |
| CAD file | 67 | $250 | $250 | $250 | N/A | Fixed add-on |
| Final Survey | 10 | $465 | $250 | $750 | $300 | |
| Commercial orders (all types) | 642 | $2,159 | — | — | — | 4.1x residential avg |

---

## County Pricing — PRODUCTION ACTUALS (Land Survey Only, 1yr, n≥10)

These are real NexGen prices, not market estimates.

| County | Orders | Avg Price | Tier |
|--------|--------|-----------|------|
| OKEECHOBEE | 20 | $1,797 | Remote/Rural |
| HIGHLANDS | 35 | $1,337 | Remote/Rural |
| MARION | 77 | $1,052 | Remote/Rural |
| CITRUS | 37 | $954 | Remote/Rural |
| CLAY | 47 | $779 | North FL |
| VOLUSIA | 92 | $734 | North FL |
| LAKE | 71 | $740 | Central FL |
| POLK | 304 | $743 | Central FL |
| ST LUCIE | 114 | $702 | Treasure Coast |
| DUVAL | 175 | $654 | North FL |
| OSCEOLA | 71 | $685 | Central FL |
| COLLIER | 225 | $643 | SW FL (Naples) |
| MARTIN | 284 | $631 | Treasure Coast |
| ORANGE | 213 | $607 | Central FL |
| PASCO | 350 | $608 | Central FL |
| INDIAN RIVER | 285 | $595 | Treasure Coast |
| CHARLOTTE | 234 | $591 | SW FL |
| MANATEE | 380 | $584 | Gulf Coast |
| PALM BEACH | 3,310 | $571 | South FL |
| HILLSBOROUGH | 680 | $575 | Central FL |
| BREVARD | 347 | $560 | Space Coast |
| SARASOTA | 502 | $555 | Gulf Coast |
| MIAMI-DADE | 587 | $547 | South FL |
| HERNANDO | 199 | $540 | Central FL |
| PINELLAS | 418 | $527 | Gulf Coast |
| ST. LUCIE | 595 | $464 | Treasure Coast |
| LEE | 947 | $500 | SW FL |
| BROWARD | 1,398 | $512 | South FL |
| SEMINOLE | 63 | $479 | Central FL |

### Monroe County (Florida Keys) — Land Survey and Elevation
Monroe avg: **$1,735** (35 orders). Premium pricing confirmed. Always flag for human review.

### Pricing Tiers for AI Reference
| Tier | Counties | Use For Estimates |
|------|----------|-------------------|
| Remote/rural | Okeechobee, Highlands, Marion, Citrus | $950–$1,800 |
| North FL / inland | Clay, Volusia, Lake, Polk, Duval, Osceola | $685–$779 |
| Treasure Coast | Martin, Indian River, Collier, Charlotte | $590–$643 |
| Central FL | Orange, Pasco, Hillsborough, Brevard, Hernando | $540–$608 |
| South FL core | Palm Beach, Broward, Miami-Dade | $512–$571 |
| Gulf coast | Lee, Sarasota, Manatee, Pinellas | $500–$555 |
| Monroe (Keys) | Monroe | $1,500–$2,500 |

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
