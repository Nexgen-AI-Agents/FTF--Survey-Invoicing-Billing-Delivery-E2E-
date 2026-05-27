# Production Data Analysis — NexGen Surveying FTF System
**Period:** 2025-05-27 to 2026-05-27 (1 year)
**Database:** nexgen_ftf_db
**Generated:** 2026-05-27

---

## ANALYSIS 1: TOTAL INVOICED AMOUNT & ORDER COUNT

| Metric | Value |
|--------|-------|
| Total payment records | 23,353 |
| Unique orders billed | 18,497 |
| Total invoiced (gross) | $13,205,323.54 |
| Avg invoice amount | $565.47 |
| Min invoice amount | -$1,500.00 (refund/credit) |
| Max invoice amount | $35,000.00 |

**Key note:** 23,353 payment records vs 18,497 unique orders = some orders have multiple payment line items (add-on services billed separately).

---

## ANALYSIS 2: SERVICE TYPE BREAKDOWN

| Service Type | Orders | Total Revenue | Avg | Min | Max |
|---|---:|---:|---:|---:|---:|
| Land Survey Only | 13,322 | $8,166,851.91 | $613.03 | -$1,500.00 | $35,000.00 |
| Land Survey and Elevation | 5,872 | $2,262,532.60 | $385.31 | -$150.00 | $12,500.00 |
| Quote | 1,724 | $1,594,682.00 | $924.99 | $0.00 | $13,800.00 |
| Boundary Survey | 992 | $563,055.00 | $567.60 | $50.00 | $10,000.00 |
| Re-Survey | 408 | $160,725.01 | $393.93 | -$400.00 | $2,800.00 |
| Elevation Certificate | 368 | $99,190.01 | $269.54 | $0.00 | $1,500.00 |
| ALTA Table A Survey | 16 | $81,200.00 | $5,075.00 | $1,500.00 | $12,500.00 |
| Spot Survey (New client) | 106 | $62,500.00 | $589.62 | $350.00 | $2,500.00 |
| Property Survey and Elevation | 118 | $40,125.00 | $340.04 | $0.00 | $1,800.00 |
| Topography Survey | 62 | $29,525.00 | $476.21 | $0.00 | $1,800.00 |
| CAD file | 69 | $16,750.00 | $242.75 | $0.00 | $250.00 |
| NULL | 7 | $10,700.00 | $1,528.57 | $0.00 | $4,500.00 |
| CAD | 29 | $6,800.00 | $234.48 | $100.00 | $400.00 |
| Update Survey | 16 | $5,575.00 | $348.44 | $150.00 | $650.00 |
| Optional ALTA Table A | 2 | $5,500.00 | $2,750.00 | $1,500.00 | $4,000.00 |
| Boundary Survey, ALTA Table A Survey | 1 | $4,800.00 | $4,800.00 | $4,800.00 | $4,800.00 |
| Final Survey | 11 | $4,650.00 | $422.73 | $0.00 | $750.00 |
| Land Survey Only, Topography Survey | 4 | $4,550.00 | $1,137.50 | $350.00 | $2,800.00 |
| Site Specific Survey | 1 | $4,500.00 | $4,500.00 | $4,500.00 | $4,500.00 |
| Land Survey and Elevation, Quote | 6 | $3,875.00 | $645.83 | $225.00 | $1,500.00 |
| Specific Purpose Survey | 3 | $3,750.00 | $1,250.00 | $750.00 | $1,800.00 |
| Tree Location | 18 | $3,750.00 | $208.33 | $100.00 | $300.00 |
| Elevation Certificate, Spot Survey (New client) | 9 | $3,450.00 | $383.33 | $275.00 | $500.00 |
| Land Survey Only, Elevation Certificate | 11 | $2,453.00 | $223.00 | $0.00 | $475.00 |
| Elevation Certificate, Boundary Survey | 10 | $2,450.00 | $245.00 | -$400.00 | $475.00 |
| Construction Survey Update | 5 | $2,200.00 | $440.00 | $350.00 | $650.00 |
| Elevation Certificate, Re-Survey | 4 | $1,975.00 | $493.75 | $150.00 | $800.00 |
| Form Board Survey | 7 | $1,950.00 | $278.57 | $0.00 | $400.00 |
| Lot Split | 4 | $1,900.00 | $475.00 | $300.00 | $850.00 |
| Quote, Boundary Survey | 1 | $1,800.00 | $1,800.00 | $1,800.00 | $1,800.00 |

**Dominance:** "Land Survey Only" = 57% of all payment records and 62% of total revenue. "Land Survey and Elevation" = 17% of records. Together these two cover 74% of all billing volume.

---

## ANALYSIS 3: TOP 30 COUNTIES BY ORDER COUNT

| County | State | Orders | Total Revenue | Avg |
|---|---|---:|---:|---:|
| PALM BEACH COUNTY | FL | 4,159 | $2,123,904.02 | $510.68 |
| BROWARD COUNTY | FL | 2,928 | $1,222,951.00 | $417.67 |
| LEE COUNTY | FL | 1,772 | $749,500.00 | $422.97 |
| PALM BEACH COUNTY | FLORIDA | 1,330 | $889,135.00 | $668.52 |
| MIAMI-DADE COUNTY | FL | 1,153 | $467,070.00 | $405.09 |
| Hillsborough County | FL | 936 | $516,855.00 | $552.20 |
| COLLIER COUNTY | FL | 748 | $384,557.50 | $514.11 |
| BROWARD COUNTY | FLORIDA | 712 | $364,335.00 | $511.71 |
| SARASOTA COUNTY | FL | 658 | $324,560.00 | $493.25 |
| ST. LUCIE COUNTY | FL | 638 | $284,236.90 | $445.51 |
| Pinellas County | FL | 593 | $284,210.00 | $479.27 |
| MANATEE COUNTY | FL | 575 | $285,190.00 | $495.98 |
| Charlotte County | FL | 502 | $220,580.00 | $439.40 |
| PASCO COUNTY | FL | 445 | $218,680.00 | $491.42 |
| Miami-Dade County | FLORIDA | 418 | $279,735.00 | $669.22 |
| INDIAN RIVER COUNTY | FL | 380 | $216,460.00 | $569.63 |
| BREVARD COUNTY | FL | 360 | $187,935.00 | $522.04 |
| Martin County | FL | 353 | $222,250.00 | $629.60 |
| Polk County | FL | 298 | $252,325.00 | $846.73 |
| Hillsborough County | FLORIDA | 269 | $177,525.00 | $659.94 |
| Orange County | FL | 248 | $137,485.00 | $554.38 |
| PINELLAS COUNTY | FLORIDA | 242 | $133,350.00 | $551.03 |
| COLLIER COUNTY | FLORIDA | 236 | $133,975.00 | $567.69 |
| Lee County | FLORIDA | 213 | $112,600.00 | $528.64 |
| Hernando County | FL | 205 | $111,985.00 | $546.27 |
| DUVAL COUNTY | FL | 192 | $107,895.00 | $561.95 |
| SARASOTA COUNTY | FLORIDA | 189 | $133,975.00 | $708.86 |
| MANATEE COUNTY | FLORIDA | 151 | $100,200.00 | $663.58 |
| ST LUCIE County | FL | 139 | $79,900.00 | $574.82 |
| BREVARD COUNTY | FLORIDA | 138 | $89,500.00 | $648.55 |

**Note:** County names appear in two variants (e.g., "PALM BEACH COUNTY FL" + "PALM BEACH COUNTY FLORIDA"). This is a data quality issue — the same county is stored with different state values. Combined, Palm Beach = ~5,489 orders, Broward = ~3,640 orders.

---

## ANALYSIS 4: MONTHLY REVENUE TREND

| Month | Orders | Total Revenue | Avg Amount |
|---|---:|---:|---:|
| May 2025 | 439 | $209,995.00 | $478.35 |
| Jun 2025 | 1,888 | $998,687.00 | $528.97 |
| Jul 2025 | 2,190 | $1,165,817.50 | $532.34 |
| Aug 2025 | 2,023 | $1,136,098.91 | $561.59 |
| Sep 2025 | 1,956 | $1,099,470.11 | $562.10 |
| Oct 2025 | 1,997 | $1,208,282.01 | $605.05 |
| Nov 2025 | 1,569 | $899,195.00 | $573.10 |
| Dec 2025 | 1,736 | $1,061,370.00 | $611.39 |
| Jan 2026 | 1,664 | $1,016,050.01 | $610.61 |
| Feb 2026 | 1,751 | $950,890.00 | $543.06 |
| Mar 2026 | 2,225 | $1,214,966.00 | $546.05 |
| Apr 2026 | 2,217 | $1,304,285.00 | $588.31 |
| May 2026 | 1,698 | $940,217.00 | $553.72 |

**Notes:**
- May 2025 is partial (only from 2025-05-27)
- Steady ~$1M/month revenue; Oct 2025 and Apr 2026 are peaks
- Average monthly volume: ~1,900 invoices/month at ~$1.01M/month
- Seasonal dip in Nov 2025; strong spring activity

---

## ANALYSIS 5: PRICE DISTRIBUTION BY SERVICE TYPE (Top 8 by Volume)

### Land Survey Only (13,322 total)
| Bucket | Count | % |
|---|---:|---:|
| <$200 | 896 | 6.7% |
| $200-299 | 418 | 3.1% |
| $300-399 | 1,586 | 11.9% |
| $400-499 | 7,023 | 52.7% |
| $500-749 | 1,581 | 11.9% |
| $750-999 | 735 | 5.5% |
| $1,000+ | 1,083 | 8.1% |

**Sweet spot: $400-499 (52.7%). Median is solidly in $400s range.**

### Land Survey and Elevation (5,872 total)
| Bucket | Count | % |
|---|---:|---:|
| <$200 | 2,592 | 44.1% |
| $200-299 | 376 | 6.4% |
| $300-399 | 434 | 7.4% |
| $400-499 | 1,650 | 28.1% |
| $500-749 | 403 | 6.9% |
| $750-999 | 144 | 2.5% |
| $1,000+ | 273 | 4.6% |

**Wide distribution — 44% under $200, likely the elevation-only add-on portion billed separately. The $400-499 cluster = full combo price.**

### Quote (1,724 total)
| Bucket | Count | % |
|---|---:|---:|
| <$200 | 153 | 8.9% |
| $200-299 | 147 | 8.5% |
| $300-399 | 54 | 3.1% |
| $400-499 | 557 | 32.3% |
| $500-749 | 303 | 17.6% |
| $750-999 | 155 | 9.0% |
| $1,000+ | 355 | 20.6% |

**Quote orders skew high — 20.6% above $1,000. Avg $925. Complex/commercial jobs come in as Quotes.**

### Boundary Survey (992 total)
| Bucket | Count | % |
|---|---:|---:|
| <$200 | 18 | 1.8% |
| $200-299 | 11 | 1.1% |
| $300-399 | 83 | 8.4% |
| $400-499 | 448 | 45.2% |
| $500-749 | 351 | 35.4% |
| $750-999 | 33 | 3.3% |
| $1,000+ | 48 | 4.8% |

**$400-$750 range covers 80.6% of Boundary Surveys.**

### Re-Survey (408 total)
| Bucket | Count | % |
|---|---:|---:|
| <$200 | 7 | 1.7% |
| $200-299 | 9 | 2.2% |
| $300-399 | 273 | 66.9% |
| $400-499 | 79 | 19.4% |
| $500-749 | 26 | 6.4% |
| $750-999 | 11 | 2.7% |
| $1,000+ | 3 | 0.7% |

**Tightly clustered: 66.9% in $300-399. Consistent pricing.**

### Elevation Certificate (368 total)
| Bucket | Count | % |
|---|---:|---:|
| <$200 | 17 | 4.6% |
| $200-299 | 326 | 88.6% |
| $300-399 | 16 | 4.3% |
| $400-499 | 4 | 1.1% |
| $500-749 | 4 | 1.1% |
| $750-999 | 0 | 0.0% |
| $1,000+ | 1 | 0.3% |

**Very tight: 88.6% at $200-299. Near-uniform pricing at ~$250.**

### Property Survey and Elevation (118 total)
| Bucket | Count | % |
|---|---:|---:|
| <$200 | 53 | 44.9% |
| $200-299 | 6 | 5.1% |
| $300-399 | 5 | 4.2% |
| $400-499 | 36 | 30.5% |
| $500-749 | 9 | 7.6% |
| $750-999 | 6 | 5.1% |
| $1,000+ | 3 | 2.5% |

### Spot Survey - New Client (106 total)
| Bucket | Count | % |
|---|---:|---:|
| <$200 | 0 | 0.0% |
| $200-299 | 0 | 0.0% |
| $300-399 | 2 | 1.9% |
| $400-499 | 0 | 0.0% |
| $500-749 | 91 | 85.8% |
| $750-999 | 7 | 6.6% |
| $1,000+ | 6 | 5.7% |

**Spot Survey is a premium tier: 85.8% in $500-749. Floor is $350, avg $590.**

---

## ANALYSIS 6: ELEVATION CERT (ng_ec FLAG) CORRELATION

| Metric | Value |
|---|---|
| Orders with ng_ec=1 flag (past year) | 2,523 |
| Of those, service is "Elevation Certificate" or "Elevation Only" | 306 (12.1%) |
| Payment records for ng_ec=1 orders | 4,942 |
| Total revenue from ng_ec=1 orders | $1,601,048.50 |
| Avg payment amount (ng_ec=1) | $323.97 |

**Key finding:** Only 12.1% of ng_ec=1 orders use "Elevation Certificate" as service name. The majority (89%) are "Land Survey and Elevation" — meaning the EC flag is set on land survey combos, not just standalone EC orders.

Top services for ng_ec=1 orders:
- Land Survey and Elevation: 4,419 records (avg $323.54)
- Elevation Certificate: 293 records (avg $266.95)
- Property Survey and Elevation: 108 records (avg $330.32)
- Land Survey Only: 61 records (avg $506.74) — likely miscategorized flag

---

## ANALYSIS 7: FLOOD ZONE DISTRIBUTION

**Total ng_orders past 1 year:** 19,363
**Orders with ng_flood containing 'A' or 'V':** 6,799 (35.1%)
**Orders with NULL/empty ng_flood:** 807 (4.2%)

### Extracted Zone Code Distribution (from FEMA map data stored in ng_flood)

| Zone Code | Count | % | Description |
|---|---:|---:|---|
| X | 11,243 | 60.6% | Minimal flood hazard (outside 500-yr floodplain) |
| AE | 3,757 | 20.2% | 100-yr floodplain, base flood elevation determined |
| X500 | 1,871 | 10.1% | 500-yr floodplain (moderate risk) |
| (no ZONE: tag) | 787 | 4.2% | NULL/empty flood data |
| AH | 613 | 3.3% | Flood depths 1-3 ft (shallow flooding) |
| A | 188 | 1.0% | 100-yr floodplain, no BFE determined |
| VE | 36 | 0.2% | Coastal high-hazard (storm surge + wave action) |
| AO | 23 | 0.1% | Sheet flow, depth 1-3 ft |
| EFF | 20 | 0.1% | Parse anomaly (effective date extracted as zone) |
| D | 15 | 0.1% | Undetermined but possible flood hazard |

**Note:** ng_flood stores the full FEMA FIRM lookup text (panel number + zone + effective date), not just the zone code. Zone codes extracted via regex `ZONE:\s*([A-Z0-9]+)`.

**High-risk (A/AE/AH/AO/VE) orders:** ~4,617 (24.8% of all orders)

---

## ANALYSIS 8: COMMERCIAL VS RESIDENTIAL

| Type | Orders | Avg Amount | Total Revenue | Min | Max |
|---|---:|---:|---:|---:|---:|
| Residential (ng_commercial=0) | 22,682 | $520.73 | $11,811,158.53 | -$800.00 | $35,000.00 |
| Commercial (ng_commercial=1) | 648 | $2,137.33 | $1,384,990.00 | -$1,500.00 | $12,500.00 |

**Commercial avg is 4.1x residential avg.** Commercial = 2.8% of volume but 10.5% of revenue.

---

## ANALYSIS 9: PAYMENT TYPE BREAKDOWN

### By ng_payment_type (encoded):
| Payment Method | Status | Count | Total | Avg |
|---|---|---:|---:|---:|
| Check (type=1) | paid | 10,310 | $4,447,374.90 | $431.37 |
| Not Specified (NULL) | unpaid | 8,173 | $6,467,884.14 | $791.37 |
| Credit Card (type=2) | paid | 4,499 | $2,164,032.49 | $481.00 |
| Check (type=1) | unpaid | 125 | $1,525.00 | $12.20 |
| Not Specified | paid | 101 | $4,725.00 | $46.78 |
| Other/ACH (type=0) | unpaid | 64 | $88,072.00 | $1,376.12 |
| Check | partial paid | 18 | $20,080.00 | $1,115.56 |
| Credit Card | unpaid | 13 | $450.00 | $34.62 |
| Credit Card | partial paid | 6 | $5,625.01 | $937.50 |

### By ng_payment_details:
| Method | Count | Total |
|---|---:|---:|
| Check | 9,454 | $4,041,439.90 |
| Not Specified | 9,190 | $6,820,994.14 |
| Client Portal | 4,543 | $2,238,536.50 |

**Key insight:** "Not Specified" has very high avg ($791) and maps almost entirely to "unpaid" status — these are invoices that have been billed but payment method not yet recorded (unpaid AR).

---

## ANALYSIS 10: TOP 20 SERVICE + COUNTY COMBINATIONS

| Service | County | State | Orders | Total Revenue | Avg |
|---|---|---|---:|---:|---:|
| Land Survey Only | Palm Beach County | FL | 2,731 | $1,407,472.01 | $515.37 |
| Land Survey and Elevation | BROWARD COUNTY | FL | 1,322 | $419,825.00 | $317.57 |
| Land Survey Only | BROWARD COUNTY | FL | 1,171 | $583,936.00 | $498.66 |
| Land Survey Only | PALM BEACH COUNTY | FLORIDA | 1,034 | $717,485.00 | $693.89 |
| Land Survey Only | Lee County | FL | 861 | $426,660.00 | $495.54 |
| Land Survey and Elevation | LEE COUNTY | FL | 685 | $208,165.00 | $303.89 |
| Land Survey Only | ST. LUCIE COUNTY | FL | 545 | $243,196.90 | $446.23 |
| Land Survey and Elevation | MIAMI-DADE COUNTY | FL | 513 | $151,465.00 | $295.25 |
| Land Survey Only | Hillsborough County | FL | 502 | $292,205.00 | $582.08 |
| Land Survey and Elevation | PALM BEACH COUNTY | FL | 463 | $196,030.00 | $423.39 |
| Land Survey Only | MIAMI-DADE COUNTY | FL | 460 | $207,025.00 | $450.05 |
| Land Survey and Elevation | COLLIER COUNTY | FL | 398 | $161,947.50 | $406.90 |
| Land Survey Only | Sarasota County | FL | 396 | $201,765.00 | $509.51 |
| Quote | Palm Beach County | FL | 395 | $243,302.00 | $615.95 |
| Land Survey Only | BROWARD COUNTY | FLORIDA | 358 | $206,960.00 | $578.10 |
| Land Survey Only | MANATEE COUNTY | FL | 301 | $169,920.00 | $564.52 |
| Land Survey Only | Pinellas County | FL | 299 | $150,010.00 | $501.71 |
| Land Survey and Elevation | Broward County | FLORIDA | 276 | $115,350.00 | $417.93 |
| Land Survey Only | PASCO COUNTY | FL | 267 | $141,535.00 | $530.09 |
| Land Survey Only | BREVARD COUNTY | FL | 252 | $138,365.00 | $549.07 |

---

## ANALYSIS 11: ORDER STATUS DISTRIBUTION (ng_orders past 1 year)

Total orders: 19,363

| ng_status | Status Description | Count | % |
|---|---|---:|---:|
| 8 | Complete | 11,966 | 61.8% |
| 0 | Canceled | 4,510 | 23.3% |
| 0 | Quote | 1,029 | 5.3% |
| 11 | On Hold | 454 | 2.3% |
| 8 | Delivered | 438 | 2.3% |
| 12 | Quote | 331 | 1.7% |
| 8 | Checking | 72 | 0.4% |
| 8 | Drafting | 72 | 0.4% |
| 2 | Assigned | 69 | 0.4% |
| 8 | Assigned | 68 | 0.4% |
| 8 | In Progress | 59 | 0.3% |
| 8 | Pending | 53 | 0.3% |
| 8 | Drafting Queue | 50 | 0.3% |
| 3 | In-Field | 48 | 0.2% |
| 6 | Checking | 32 | 0.2% |
| 5 | Drafting Queue | 25 | 0.1% |
| 4 | Drafting Queue | 21 | 0.1% |
| 1 | Pending | 18 | 0.1% |
| 5 | Drafting | 17 | 0.1% |
| 7 | Complete | 8 | 0.0% |

**Key insight:** ng_status=8 covers many different status_desc values (Complete, Delivered, Checking, Drafting, etc.) — it appears to be an "in-pipeline" flag, not a single terminal state. The ng_status_desc is the reliable human-readable status.

**Active WIP orders (non-Complete, non-Canceled, non-Quote):** ~1,005 orders in pipeline at any given time.

---

## ANALYSIS 12: ORDERS ABOVE 1.5x CATALOGUE PRICE

Catalogue (ng_survey_steps) contains 24 services.

| Service | Cat Price | 1.5x Threshold | Avg Actual | Count |
|---|---:|---:|---:|---:|
| ALTA Table A Survey | $1,500 | $2,250 | $5,313 | 15 |
| Specific Purpose Survey | $600 | $900 | $1,500 | 2 |
| Lot Split | $450 | $675 | $850 | 1 |
| Boundary Survey | $350 | $525 | $1,266 | 161 |
| Final Survey | $300 | $450 | $644 | 4 |
| Update Survey | $250 | $375 | $517 | 3 |
| Form Board Survey | $225 | $338 | $362 | 4 |
| Topography Survey | $225 | $338 | $714 | 33 |
| Elevation Certificate | $225 | $338 | $484 | 16 |
| Other Services | $150 | $225 | $319 | 4 |
| Site Plan | $150 | $225 | $400 | 2 |
| Property Flagging | $150 | $225 | $450 | 2 |

**Notable:** ALTA Table A has avg actual $5,313 vs catalogue $1,500 — 3.5x over. 161 Boundary Survey overrides (16% of all Boundary Surveys billed above 1.5x cat). Boundary Survey catalogue is $350 but avg actual when over-threshold is $1,266.

**Also notable:** The two most-common services (Land Survey Only, Land Survey and Elevation) are NOT in ng_survey_steps — they have no catalogue price. This is the single biggest gap.

---

## ANALYSIS 13: NON-STANDARD SERVICE NAMES (not in ng_survey_steps)

**Catalogue has 24 official steps.** 17 of those appear in production orders.

### High-volume non-standard services (these SHOULD be in catalogue):
| Service Name | Orders (past year) |
|---|---:|
| Land Survey Only | 12,118 |
| Land Survey and Elevation | 2,878 |
| Quote | 2,135 |
| Re-Survey | 391 |
| Spot Survey (New client) | 106 |
| CAD file | 72 |
| Property Survey and Elevation | 65 |
| CAD | 29 |

### Standard catalogue services that appear in orders:
| Service Name | Orders |
|---|---:|
| Boundary Survey | 984 |
| Elevation Certificate | 361 |
| Topography Survey | 37 |
| ALTA Table A Survey | 17 |
| Update Survey | 16 |
| Property Flagging | 8 |
| Final Survey | 8 |
| Tree Location | 6 |
| Other Services | 5 |
| Form Board Survey | 5 |
| Elevation Only | 3 |
| Site Plan | 3 |
| Sketch and Description | 3 |
| Specific Purpose Survey | 2 |
| Legal Description | 1 |
| Lot Split | 1 |
| Survey Re-draw | 1 |

### Missing from catalogue entirely (no ng_survey_steps entry):
- Land Survey Only (most common by far — 12,118 orders)
- Land Survey and Elevation (2,878 orders)
- Quote (2,135 orders)
- Re-Survey (391 orders)
- Spot Survey (New client) / Spot Survey (Prior NexGen Survey)
- CAD file / CAD
- Property Survey and Elevation
- Resurvey, Re-stake, RE-FLAG CORNERS
- Various combo services (comma-separated)

---

## ANALYSIS 14: MULTI-SERVICE ORDERS

| Metric | Value |
|---|---|
| Total orders with service name | 19,363 |
| Orders with comma in service | 58 (0.3%) |
| Orders with semicolon in service | 0 |
| True multi-service orders | 58 (0.3%) |
| Orders with NULL/empty service | 18 |

**"Land Survey and Elevation" is a single-service name (NOT multi-service).**

Top multi-service combos (comma-separated):
- Elevation Certificate, Boundary Survey: 6 orders
- Land Survey Only, Elevation Certificate: 5 orders
- Elevation Certificate, Spot Survey (New client): 4 orders
- Land Survey Only, Quote: 3 orders
- Land Survey and Elevation, Quote: 3 orders

Multi-service is rare (0.3%). The system generally handles add-ons as separate payment line items rather than combined service names.

---

## BONUS: PAYMENT STATUS SUMMARY

| Status | Count | Total | Avg | % by Count |
|---|---:|---:|---:|---:|
| paid | 14,920 | $6,620,487.39 | $443.73 | 63.9% |
| unpaid | 8,375 | $6,557,931.14 | $783.04 | 35.9% |
| partial paid | 29 | $29,155.01 | $1,005.35 | 0.1% |
| NULL | 29 | -$2,250.00 | -$77.59 | 0.1% |

**Outstanding AR (unpaid): $6,557,931.14 across 8,375 invoices**
**Collection rate: 50.1% of billed revenue collected within period**
**Unpaid avg ($783) vs paid avg ($444) — larger invoices take longer to collect**

---

## BONUS: DAYS TO PAYMENT ANALYSIS (paid invoices)

| Metric | Value |
|---|---|
| Paid invoice count | 14,912 |
| Avg days billed to paid | 26.5 days |
| Min days | -13 (prepaid) |
| Max days | 316 days |
| Same day or prepaid | 1,461 (9.8%) |
| 1-30 days | 7,881 (52.9%) |
| 31-60 days | 4,385 (29.4%) |
| 61-90 days | 777 (5.2%) |
| >90 days | 408 (2.7%) |

**62.7% of invoices collected within 30 days. 92.1% within 60 days. Long tail: 408 invoices (2.7%) take over 90 days.**

---

## BONUS: TOP 15 ACCOUNTS BY REVENUE (past 1 year)

| Rank | Account Name | Email | Orders | Total Revenue |
|---|---|---|---:|---:|
| 1 | Sydney Harris Coordinators | project-coordination@boselectric.com | 357 | $201,300.00 |
| 2 | Main Office (Preferred Settlement) | orders@preferredsettlement.com | 408 | $191,875.00 |
| 3 | Team Account (First American) | brandonclosings@firstam.com | 273 | $154,550.00 |
| 4 | Sophia Sfirakis (Standard Closing FL) | processing@standardclosingfl.com | 242 | $112,250.00 |
| 5 | Florida Team (Homeward Title) | floridateam@homewardtitle.com | 220 | $91,495.00 |
| 6 | ADAM GILMAN (Deck & Drive) | permits@deckanddrive.com | 174 | $89,210.00 |
| 7 | Lulich Closings Team | closings@lulich.com | 173 | $88,865.00 |
| 8 | Joseph McSherry (Assurity Title) | Joe@AssurityTitle.com | 135 | $88,050.00 |
| 9 | AMANDA BURNETT (Encore Title) | amanda@encoretitlegroup.com | 156 | $85,700.00 |
| 10 | Southeast Title | orders@setitle.com | 163 | $69,100.00 |
| 11 | Chris Bernhardt (Florida State Fence) | chris@floridastatefence.com | 151 | $61,675.00 |
| 12 | Candy Eckhoff (Cohen Norris) | ce@cohennorris.com | 130 | $60,075.00 |
| 13 | ANGELA HYNDMAN (Premiere Title) | Angie@premieretitleservices.com | 194 | $59,000.00 |
| 14 | Wendy Burns | wendy.burns@dkpalaw.com | 142 | $54,650.00 |
| 15 | NICOLE MONTGOMERY (Closing Team FL) | nicole@closingteamfl.com | 136 | $53,340.00 |

---

## KEY SCHEMA NOTES (for AI agent use)

### ng_payments
- `ng_payment_type`: 1=Check, 2=Credit Card, 0=Other/ACH. NULL/empty = unrecorded
- `ng_payment_details`: 'check', 'Client' (portal), or staff username
- `ng_status`: 'paid', 'unpaid', 'partial paid' (varchar, not tinyint)
- `payment_status`: 0=unpaid, 1=paid, 2=partial paid (int — mirrors ng_status)
- `ng_amount`: invoice amount (can be negative for refunds/credits)
- `ng_work_done`: service category label (different from ng_orders.ng_service_requested)
- `ng_order`: VARCHAR — cast with CAST(ng_order AS UNSIGNED) to join to ng_orders.ng_order (BIGINT)
- `paid_amount`: amount actually collected (for partial pay tracking)

### ng_orders
- `ng_service_requested`: longtext — free text, not always from catalogue. Main volume services (Land Survey Only, Land Survey and Elevation) NOT in ng_survey_steps
- `ng_status`: tinyint — NOT a simple 0/1/2 enum. 0=various, 8=in-pipeline, 11=On Hold, 12=Quote
- `ng_status_desc`: varchar — the human-readable status (Complete, Canceled, In-Field, etc.)
- `ng_ec`: tinyint flag — elevation cert involved. Set on Land Survey and Elevation combos, not just EC-only orders
- `ng_flood`: full FEMA FIRM text (panel # + ZONE: XX + EFF date). Extract zone with regex
- `ng_commercial`: 1=commercial, 0=residential
- `ng_dtentered`: datetime — order entry date (use for order-level date filtering)
- `ng_date_gen_invoice`: date — invoice generation date (may differ from ng_date_billed in payments)
- `ng_date_delivered`: datetime — delivery date

### ng_survey_steps (catalogue)
- Only 24 entries. The top 4 services by volume (Land Survey Only, Land Survey and Elevation, Quote, Re-Survey) are NOT in this table.
- `ng_rate` is INT (dollars, no cents)

### Data Quality Issues Discovered
1. **County name inconsistency**: Same county stored as both "PALM BEACH COUNTY / FL" and "PALM BEACH COUNTY / FLORIDA" — deduplication needed for county-level reporting
2. **Service name not normalized**: Free-text ng_service_requested has 80+ distinct values; most common services not in catalogue
3. **ng_flood stores raw text**: Not a simple zone code — requires text parsing
4. **Multi-payment per order**: 23,353 payment records for 18,497 unique orders (some orders split into multiple line items)
5. **ng_status=8 is overloaded**: Maps to Complete, Delivered, Checking, Drafting, etc. — always use ng_status_desc for display
