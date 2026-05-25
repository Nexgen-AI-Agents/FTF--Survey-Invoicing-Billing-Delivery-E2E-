# FTF API — Confirmed Response Schemas

Probed: 2026-05-25 against staging (`stage.fieldtofinish.jobs/ftf-ai-api/v1`)

---

## GET /orders — Bulk Endpoint

Returns paginated envelope: `{"count", "data", "limit", "offset", "success", "total"}`

Each order in `data[]` has **7 fields only**:

| Field | Type | Notes |
|-------|------|-------|
| `order_id` | int | Cast to str for DB operations |
| `customer_id` | str | UUID-style string |
| `status` | str | FTF pipeline status (Quote, Assigned, etc.) |
| `service_type` | str | Always `"Quote"` for status=Quote orders — NOT the actual service name |
| `property_address` | str | Street address only — no lat/lng |
| `estimate_sent` | bool | True if estimate already dispatched |
| `created_at` | str | ISO datetime |

**Important:** `service_type` returns `"Quote"` for ALL orders fetched with `?status=Quote`. Actual service name is NOT available from this endpoint.

---

## GET /orders/{id} — Individual Order Endpoint

Returns `{"data": {...}, "success": true}`

Full field list (26 fields confirmed):

| Field | Type | Example | Sprint 2 Relevance |
|-------|------|---------|-------------------|
| `order_id` | int | `1000276038` | Primary key |
| `customer_id` | str | `"202601190525338175"` | Link to customer |
| `company_id` | str | `"202601190525338095"` | B2B company link |
| `status` | str | `"Quote"` | Pipeline status |
| `status_code` | int | `12` | Numeric status (12 = Quote) |
| `service_type` | str | `"Land Survey Only"`, `"Re-survey"`, `"Quote"` | **Actual service name — or "Quote" if FTF staff haven't classified yet** |
| `customer_name` | str | `"sourabhtest"` | Display name |
| `customer_email` | str | `"user@domain.com"` | **Classifier uses this — no separate customer call needed** |
| `customer_type` | str | `"individual"` or `"b2b"` | **Pricing tier — individual vs B2B** |
| `property_address` | str | `"231 FL-121"` | Street only |
| `property_city` | str | `"WILLISTON"` | |
| `property_county` | str | `"Levy County"` | Used for local pricing rules |
| `property_state` | str | `"FLORIDA"` | |
| `property_zip` | str | `"32696"` | |
| `property_lat` | str | `"29.3345244"` | **Lat — always present — no geocoding needed** |
| `property_lng` | str | `"-82.51504729999999"` | **Lng — always present — no geocoding needed** |
| `flood_zone` | str or null | `"12099C0367F\nZONE;X\nEFF: 10/05/2017"` | **Pre-populated by FTF for most orders — skip FEMA call if not null** |
| `elevation_cert` | bool | `false` | Whether elevation certificate is needed |
| `special_pricing` | bool | `false` | Override pricing flag |
| `estimate_sent` | bool | `false` | Already dispatched flag |
| `invoiced` | bool | `false` | Billing flag |
| `paid` | bool | `false` | Payment flag |
| `due_amount` | float | `0.0` | Outstanding balance |
| `created_at` | str | `"2026-01-28T00:16:43"` | ISO datetime |
| `updated_at` | str | `"2026-01-28T00:16:47"` | ISO datetime |
| `fieldwork_at` | str or null | `null` | When field crew worked the order |
| `delivered_at` | str or null | `null` | When order was delivered |

### Critical Findings

**service_type behavior:**
- If FTF staff have classified the order → returns actual name (e.g., `"Land Survey Only"`, `"Re-survey"`, `"ALTA Table A Survey"`)
- If FTF staff have NOT classified it yet → returns `"Quote"`
- Classifier must handle both cases: use `service_type` when available, apply fallback logic when `service_type == "Quote"`

**flood_zone pre-population:**
- FTF already runs FEMA lookup and stores the result in `flood_zone`
- Format: `"12099C0367F\nZONE;X\nEFF: 10/05/2017"` — panel number, zone, effective date on separate lines
- When `flood_zone` is not null → use directly, skip FEMA API call
- When `flood_zone` is null → call FEMA API using `property_lat` / `property_lng`

**lat/lng always present:**
- `property_lat` and `property_lng` are always populated (confirmed across all probed orders)
- Both are strings — cast to float before passing to FEMA API: `float(order["property_lat"])`

**customer_type in order:**
- `customer_type` (`"individual"` or `"b2b"`) is included in the order response
- Classifier does NOT need a separate `GET /customers/{id}` call just for customer type

---

## GET /customers/{id} — Individual Customer Endpoint

Returns `{"data": {...}, "success": true}`

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `customer_id` | str | `"202601190525338175"` | Primary key |
| `company_id` | str | `"202601190525338095"` | Company link |
| `company_name` | str | `"sourabhtest"` | |
| `first_name` | str | `"sourabhtest"` | |
| `last_name` | str | `" "` | May be blank |
| `email` | str | `"user@domain.com"` | Email field name confirmed as `email` (not `customer_email`) |
| `phone` | str | `"5847485869"` | |
| `customer_type` | str | `"individual"` or `"b2b"` | Same as in order response |
| `pricing_type` | int | `0` | `0` = individual pricing, `1` = B2B pricing (unconfirmed — needs FTF confirmation) |
| `special_pricing` | bool | `false` | Override pricing flag |
| `custom_rate` | float or null | `null` | Custom negotiated rate if set |
| `created_at` | str or null | `null` | May be null |

### When to call GET /customers/{id}

Only needed when the Classifier needs `pricing_type`, `custom_rate`, or `special_pricing` at the customer level. For `customer_type` and `email`, the order response already provides these.

---

## Sprint 2 Classifier Architecture — Implications

Based on confirmed schemas, the Classifier (Agent 3) should:

1. Call `GET /orders/{id}` for each pending order — one call gives: service_type, customer_type, customer_email, lat, lng, flood_zone, elevation_cert, special_pricing
2. If `service_type != "Quote"` → use it directly for classification
3. If `service_type == "Quote"` → apply fallback: flag order for Robert/Mark review (cannot auto-classify)
4. If `flood_zone` is not null → use it directly, skip FEMA API
5. If `flood_zone` is null → call FEMA with `float(property_lat)`, `float(property_lng)`
6. Call `GET /customers/{id}` only if `custom_rate` or `pricing_type` override logic is needed

This means: **no geocoding service needed**, **FEMA calls reduced to orders with null flood_zone only**, and **customer endpoint calls minimized to cases requiring custom rate data**.
