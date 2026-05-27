# FTF Production Invoice Analysis — May 2025 to May 2026
# Source: nexgen_ftf_db (AWS RDS prod) — direct query 2026-05-27
# 23,353 payment records | 18,497 unique orders | $13.2M invoiced

---

## HEADLINE NUMBERS

| Metric | Value |
|--------|-------|
| Total invoiced (1 yr) | $13,205,323 |
| Total payment records | 23,353 |
| Unique orders billed | ~18,497 |
| Avg invoice amount | $565 |
| AR outstanding (unpaid) | $6,565,086 (8,212 invoices) |
| Unpaid rate | ~35.9% |
| Commercial orders | 2.8% of volume, 10.5% of revenue |
| Avg commercial price | $2,159 |
| Avg residential price | $527 |

---

## CRITICAL FINDING: Top 2 Services Are NOT in ng_survey_steps Catalogue

The two dominant services in production do NOT exist in the official pricing catalogue:

| Service Name | Orders (1yr) | Total Revenue | Avg Price | Catalogue? |
|---|---|---|---|---|
| **Land Survey Only** | 13,260 | $8,170,826 | $616 | ❌ NOT IN CATALOGUE |
| **Land Survey and Elevation** | 5,654 | $2,262,682 | $400 | ❌ NOT IN CATALOGUE |
| Quote | 1,721 | $1,594,682 | $926 | ❌ Unclassified |
| Boundary Survey | 992 | $563,055 | $567 | ✅ Catalogue: $350 |
| Re-Survey | 406 | $161,475 | $397 | ❌ NOT (alias: Update Survey) |
| Elevation Certificate | 365 | $99,190 | $271 | ✅ Catalogue: $225 |
| Property Survey and Elevation | 114 | $40,125 | $351 | ❌ NOT IN CATALOGUE |
| Spot Survey (New client) | 106 | $62,500 | $589 | ❌ NOT IN CATALOGUE |
| CAD file | 67 | $16,750 | $250 | ❌ NOT IN CATALOGUE |
| Topography Survey | 61 | $29,525 | $484 | ✅ Catalogue: $225 |
| ALTA Table A Survey | 16 | $81,200 | $5,075 | ✅ Catalogue: $1,500 |
| Update Survey | 16 | $5,575 | $348 | ✅ Catalogue: $250 |
| Final Survey | 10 | $4,650 | $465 | ✅ Catalogue: $300 |

### What This Means for AI Classifier
"Land Survey Only" = 57% of all orders. The classifier must treat this as an alias for
Boundary Survey in the pricing logic, but with DIFFERENT actual pricing ($400-616 avg, not $350).
The catalogue base price of $350 is the FLOOR, not the typical charge.

### Service Type Alias Map (production-confirmed)
| Production CRM Label | Maps To | Avg Actual Price |
|---|---|---|
| Land Survey Only | Boundary Survey | $400–$616 (county-dependent) |
| Land Survey and Elevation | Boundary Survey + Elevation bundle | $350–$650 |
| Property Survey and Elevation | Boundary Survey + Elevation bundle | $351 |
| Re-Survey | Update Survey | $397 |
| Spot Survey (New client) | Foundation Tie-In (first-time) | $589 |
| Spot Survey (Prior NexGen Survey) | Foundation Tie-In (return) | $300 |
| CAD file / CAD | Survey Re-draw / CAD export | $250 |
| Construction Survey | Topography Survey | ~$440 |
| Lot split Survey | Lot Split | $312 |
| As-Built Survey | Final Survey | ~$465 |
| Update/Topo | Update Survey or Topography | variable |
| Re-Flag Corners | Property Flagging | ~$225 |
| Line Stake Out | Building Stake Out / Pad Stake Out | ~$225 |
| Construction Survey Update | Topography Survey (update) | $440 |

---

## REAL PRICING: Land Survey Only by County (production actuals, 1yr, n>=10)

These are ACTUAL prices NexGen charges — far more accurate than the $350 catalogue.

| County | Orders | Avg Price | Min | Max |
|--------|--------|-----------|-----|-----|
| OKEECHOBEE | 20 | $1,797 | $700 | $3,800 |
| HIGHLANDS | 35 | $1,337 | $575 | $5,000 |
| CITRUS | 37 | $954 | $475 | $4,800 |
| MARION | 77 | $1,052 | $300 | $5,000 |
| CLAY | 47 | $779 | $225 | $5,000 |
| LAKE | 71 | $740 | $250 | $3,500 |
| VOLUSIA | 92 | $734 | $250 | $4,500 |
| ST LUCIE (dup) | 114 | $702 | $200 | $4,800 |
| DUVAL | 175 | $654 | $200 | $4,800 |
| OSCEOLA | 71 | $685 | $250 | $3,500 |
| COLLIER | 225 | $643 | $200 | $3,800 |
| MARTIN | 284 | $631 | $200 | $4,800 |
| INDIAN RIVER | 285 | $595 | $200 | $4,800 |
| CHARLOTTE | 234 | $591 | $250 | $4,800 |
| PASCO | 350 | $608 | $200 | $4,800 |
| ORANGE | 213 | $607 | $200 | $4,500 |
| MANATEE | 380 | $584 | $250 | $4,800 |
| PALM BEACH | 3,310 | $571 | $200 | $5,000 |
| HILLSBOROUGH | 680 | $575 | $200 | $4,800 |
| BREVARD | 347 | $560 | $200 | $4,800 |
| INDIAN RIVER | 285 | $595 | $200 | $4,800 |
| MIAMI-DADE | 587 | $547 | $200 | $4,800 |
| HERNANDO | 199 | $540 | $275 | $4,400 |
| SARASOTA | 502 | $555 | $200 | $4,800 |
| PINELLAS | 418 | $527 | $200 | $3,500 |
| BROWARD | 1,398 | $512 | $200 | $5,000 |
| LEE | 947 | $500 | $225 | $4,800 |
| ST. LUCIE | 595 | $464 | $200 | $3,800 |
| SEMINOLE | 63 | $479 | $250 | $1,800 |

### County Pricing Tiers (Land Survey Only)
| Tier | Counties | Typical Avg |
|------|----------|-------------|
| Remote/rural (far from crew) | Okeechobee, Highlands, Citrus, Marion | $950–$1,800 |
| North/inland FL | Clay, Lake, Volusia, Duval, Osceola | $685–$779 |
| Treasure Coast + Collier | Martin, Indian River, Collier, Charlotte | $590–$643 |
| South FL core | Palm Beach, Broward, Miami-Dade | $512–$571 |
| Gulf Coast | Lee, Sarasota, Manatee, Pinellas, Hillsborough | $500–$584 |
| Central + Pasco | Orange, Pasco, Hernando, Brevard | $540–$608 |

### Monroe County (Florida Keys) — Land Survey and Elevation
Monroe County shows avg **$1,735** for "Land Survey and Elevation" (35 orders).
This confirms the Monroe County flag in the classifier is correct — non-standard pricing.

---

## REAL PRICING: Land Survey and Elevation by County

| County | Orders | Avg Price |
|--------|--------|-----------|
| MONROE | 35 | $1,735 |
| VOLUSIA | 14 | $818 |
| ST. JOHNS | 13 | $834 |
| MARTIN | 24 | $721 |
| INDIAN RIVER | 45 | $686 |
| ORANGE | 11 | $672 |
| HILLSBOROUGH | 108 | $631 |
| SARASOTA | 99 | $614 |
| PALM BEACH | 402 | $596 |
| COLLIER | 277 | $599 |
| PINELLAS | 155 | $546 |
| MIAMI-DADE | 376 | $514 |
| LEE | 397 | $513 |
| MANATEE | 119 | $510 |
| BROWARD | 861 | $518 |
| PASCO | 68 | $466 |
| CHARLOTTE | 144 | $484 |
| BREVARD | 28 | $457 |

**Note:** 2,750 of 5,654 "Land Survey and Elevation" records are <$300 (avg $153).
These are likely partial billing entries (elevation portion only) for bundled orders.

---

## PRICE DISTRIBUTION: Land Survey Only

| Price Bucket | Orders | Avg |
|---|---|---|
| <$350 (below catalogue) | 1,467 | $170 |
| $350–$399 | 1,371 | $373 |
| **$400–$449** | **4,691** | **$400** (most common) |
| $450–$499 | 2,332 | $464 |
| $500–$549 | 448 | $505 |
| $550–$599 | 572 | $562 |
| $600–$699 | 483 | $635 |
| $700–$799 | 382 | $744 |
| $800–$999 | 432 | $861 |
| $1,000+ | 1,083 | $2,711 |

**Takeaway:** Most common price = $400–$449 (35% of orders). Catalogue says $350 — reality is $400 base. $1,000+ orders (8%) are commercial or complex rural jobs.

---

## COMMERCIAL vs RESIDENTIAL

| Type | Orders | Avg Price | Total Revenue |
|------|--------|-----------|---------------|
| Residential (ng_commercial=0) | 22,389 | $527 | $11,815,733 |
| Commercial (ng_commercial=1) | 642 | $2,159 | $1,386,490 |

**Commercial multiplier: 4.1x residential price.**
Commercial is 2.8% of volume but 10.5% of revenue.

---

## ALTA TABLE A SURVEY — Actual vs Catalogue

| Metric | Value |
|--------|-------|
| Catalogue price | $1,500 |
| Production avg | $5,075 |
| Min | $1,500 |
| Max | $12,500 |
| Orders (1yr) | 16 |

ALTA is billed 3.4x the catalogue price. The $1,500 catalogue is just the floor/starting point.
Each ALTA is custom-priced based on scope.

---

## FLOOD ZONE DATA

The `ng_flood` field stores full FEMA flood map panel text (e.g., "12099C0770F\nZONE: X\nEFF: 10/05/2017").
Parse logic: extract "ZONE: " from the text.

- Most common zone in prod: Zone X (no flood hazard) — majority of orders
- Zone AE (100-yr flood): significant volume (e.g., "ZONE: AE\nELEV: 06 FT")
- Zone X500 (500-yr moderate hazard): also present
- Zone V/VE: rare but always flagged for human review (confirmed correct)

**Parsing note for classifier:** `ng_flood` is NOT a simple "AE" string — it's multi-line with panel number, zone, and effective date. AI pipeline must parse for "ZONE: " substring.

---

## MONTHLY REVENUE TREND (May 2025 – May 2026)

| Month | Orders Billed | Revenue |
|-------|---------------|---------|
| 2025-05 | 415 | $209,995 |
| 2025-06 | 1,803 | $998,687 |
| 2025-07 | 2,090 | $1,165,817 |
| 2025-08 | 2,020 | $1,136,098 |
| 2025-09 | 1,944 | $1,100,770 |
| 2025-10 | 1,990 | $1,208,782 |
| 2025-11 | 1,564 | $899,195 |
| 2025-12 | 1,724 | $1,061,520 |
| 2026-01 | 1,657 | $1,016,150 |
| 2026-02 | 1,723 | $950,890 |
| 2026-03 | 2,219 | $1,217,541 |
| 2026-04 | 2,212 | $1,304,785 |
| 2026-05 | 1,692 | $941,167 |

Peak months: March–April and July–October.
Slowest: November–February (winter/holiday lull).
Target: ~$1.1M/month run rate.

---

## TOP COUNTIES BY ORDER VOLUME (all services, 1yr)

(After normalizing FL/FLORIDA duplicate — combine both)

| County | Est. Orders | Est. Avg Price |
|--------|-------------|----------------|
| PALM BEACH | ~5,446 | $580 |
| BROWARD | ~3,541 | $470 |
| LEE | ~1,951 | $490 |
| MIAMI-DADE | ~1,549 | $480 |
| HILLSBOROUGH | ~1,204 | $575 |
| COLLIER | ~968 | $535 |
| SARASOTA | ~843 | $520 |
| PINELLAS | ~831 | $495 |
| MANATEE | ~721 | $520 |
| PASCO | ~508 | $490 |
| ST. LUCIE | ~770 | $470 |
| MARTIN | ~374 | $640 |
| BREVARD | ~490 | $545 |
| INDIAN RIVER | ~424 | $580 |
| CHARLOTTE | ~499 | $440 |
| POLK | ~296 | $852 |

---

## AR OUTSTANDING — $6.56M UNPAID

| Metric | Value |
|--------|-------|
| Unpaid invoices | 8,212 |
| Total AR outstanding | $6,565,086 |
| Payment type=NULL status=unpaid | 8,128 records ($6.47M) |

**Payment types:**
- Type 1 (Check): 10,307 paid records ($4.45M)
- Type 2 (Credit Card): 4,492 paid records ($2.16M)
- Type NULL (unpaid): 8,128 records ($6.47M)
- Type 0: 79 records (mix paid/unpaid)

---

## NON-STANDARD SERVICE NAMES IN PRODUCTION (past 1yr)

These appear in ng_orders.ng_service_requested but NOT in ng_survey_steps.
Listed by frequency — these are the aliases the classifier must handle:

| Production Label | Count | Action |
|---|---|---|
| Land Survey Only | 12,119 | → Boundary Survey (most common) |
| Land Survey and Elevation | 2,878 | → Boundary Survey + EC bundle |
| Quote | 2,135 | → flag for human (unclassified) |
| Re-Survey | 391 | → Update Survey |
| Spot Survey (New client) | 106 | → Foundation Tie-In |
| CAD file | 72 | → Survey Re-draw |
| Property Survey and Elevation | 65 | → Boundary + EC bundle |
| CAD | 29 | → Survey Re-draw |
| Elevation Certificate, Boundary Survey | 6 | → multi-service |
| Land Survey Only, Elevation Certificate | 5 | → multi-service |
| Spot Survey (Prior NexGen Survey) | 3 | → Foundation Tie-In (repeat) |
| Re-Flag Corners | 2 | → Property Flagging |
| Line Stake Out | 2 | → Building Stake Out |
| Cancel after office prep (10%) | 2 | → cancellation partial billing |
| Update/Topo | 2 | → Update Survey or Topo |
| Expedited Rush Survey | 1 | → flag + surcharge |
| As-Built Survey | 1 | → Final Survey |
| Construction Survey | 1 | → Topography Survey |
| Offset Staking | 1 | → Building Stake Out |
| Cancel after field work (50%) | 1 | → cancellation 50% billing |
| ALTA Conversion | 1 | → ALTA Table A Survey (conversion job) |
| Topo upgrade | 1 | → Topography Survey (add-on) |
| Finished Floor Elevation on Survey | 1 | → Elevation Certificate add-on |

---

## MULTI-SERVICE ORDERS

58 orders have comma/concatenated service names in ng_service_requested.
The system typically bills add-ons as SEPARATE payment line items on the same ng_order
(not concatenated in service_requested). This is the dominant pattern for multi-service billing.

Common multi-service combos found:
- Land Survey Only, Elevation Certificate (10 orders — but mostly billed as 2 line items)
- Land Survey Only, Topography Survey (4 orders)
- Elevation Certificate, Boundary Survey (9 orders)
- Site Plan, Update Survey, 3rd Party Digital Signature (3 orders)

---

## AI PIPELINE IMPLICATIONS

### Issues Now Resolved by This Data:

1. **I-039 / I-051 (Service aliases):** "Land Survey Only" = Boundary Survey but priced $400-$616.
   Classifier must normalize to Boundary Survey, but pricing engine must use county-actual not catalogue.

2. **I-047 (County pricing matrix):** Real production data supersedes research estimates.
   Use the county avg table above for pricing AI context.

3. **Flood zone parsing:** `ng_flood` is multi-line text. AI must substring-search for "ZONE: AE/VE/V/A"
   — not a direct zone code comparison.

4. **Commercial pricing:** 4.1x residential. Flag all commercial orders for human review (Bobby/Robert).

5. **ALTA actual pricing:** $5,075 avg (not $1,500 catalogue). Always flag for human review — correct.

6. **Monroe County confirmed:** $1,735 avg for bundled service — premium pricing confirmed.
   Monroe flag is correctly set.

7. **AR intelligence:** $6.56M outstanding. Jessica's AR agent context: avg days-to-pay ~26.5,
   92% collected within 60 days.

8. **Monthly volume target:** ~$1.1M/month = ~1,900-2,200 orders billed. March/April peak, Nov–Jan slow.

### Pricing AI Prompt Context (use this):
- Base "Land Survey Only" price: $400 (not $350). County modifier on top.
- Remote/rural FL (Okeechobee, Highlands, Citrus, Marion): 2–4x base price.
- Monroe County: 3x+ base price. Always human review.
- Commercial jobs: 4x residential base. Always human review.
- ALTA: $1,500 catalogue is floor. Actual avg $5,075. Custom per scope. Always flag.
- The AI should never auto-quote below $350 for any Boundary/Land Survey.

---
*Last updated: 2026-05-27. Refresh quarterly or when prod schema changes.*
