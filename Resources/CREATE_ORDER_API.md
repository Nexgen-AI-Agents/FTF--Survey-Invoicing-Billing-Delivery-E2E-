# FTF AI API — Create Order

**Endpoint:** `POST /ftf-ai-api/v1/orders`  
**Auth:** Required — `X-API-Key` header (or `Authorization: Bearer <key>`)  
**Content-Type:** `application/json`

---

## Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `customer_id` | integer | ✅ | `ng_accounts.ng_account_id` — the ordering customer |
| `property_address` | string | ✅ | Street address of the survey property |
| `service_type` | string | ✅ | Service requested (must match a value in `ng_survey_steps.ng_step`) |
| `property_city` | string | — | City |
| `property_state` | string | — | 2-letter state code (stored uppercase) |
| `property_zip` | string | — | ZIP code |
| `property_county` | string | — | County name |
| `elevation_cert` | boolean | — | `true` sets `ng_ec = 1` (default `false`) |
| `notes` | string | — | Internal office notes stored in `ng_notes` |
| `date_needed` | string | — | Surveyor deadline — `YYYY-MM-DD` format |
| `status` | string | — | `"pending"` (default) or `"quote"` |

### Example

```json
{
  "customer_id": 1042,
  "property_address": "123 Oak Street",
  "property_city": "Fort Lauderdale",
  "property_state": "FL",
  "property_zip": "33301",
  "property_county": "Broward",
  "service_type": "Land Survey Only",
  "elevation_cert": false,
  "notes": "Gate code: 1234",
  "date_needed": "2026-06-15",
  "status": "pending"
}
```

---

## Response

### 201 Created

```json
{
  "success": true,
  "order_id": 10527,
  "status": "Pending",
  "customer_id": 1042,
  "property_address": "123 OAK STREET",
  "service_type": "Land Survey Only",
  "created_at": "2026-05-27T14:32:00.123456"
}
```

### Error Responses

| HTTP | `error` code | Cause |
|---|---|---|
| 400 | `empty_body` | No JSON body sent |
| 400 | `missing_field` | `customer_id`, `property_address`, or `service_type` absent |
| 400 | `invalid_status` | `status` is not `pending` or `quote` |
| 400 | `invalid_date` | `date_needed` is not `YYYY-MM-DD` |
| 401 | `invalid_api_key` | API key missing or unrecognised |
| 404 | `customer_not_found` | `customer_id` not in `ng_accounts` |
| 500 | (exception message) | Unexpected server error |

---

## What the Endpoint Does

1. Validates all required fields and the optional `status` / `date_needed` inputs.
2. Looks up the customer in `ng_accounts` to derive `ng_company_id`, `ng_email`, and name fields automatically.
3. Generates the next `ng_order` ID as `MAX(ng_orders.ng_order) + 1`.
4. Inserts a row into `ng_orders` with:
   - `ng_status = 1` (Pending) or `12` (Quote)
   - `ng_fieldpack = 1`, `ng_invoice_needed = 1` (standard defaults)
   - `ng_dtentered = NOW()`
5. Logs the creation to `ng_log_trackflow` (actor: `"Created"`, type: `"AI API Order"`).

---

## Status Values for New Orders

| `status` param | `ng_status` | Display |
|---|---|---|
| `pending` (default) | `1` | Pending |
| `quote` | `12` | Quote |

To move an order to any other status after creation, use the standard web UI or a future PATCH endpoint.

---

## Service Type Values

`service_type` is a free-text field stored in `ng_service_requested`. Common values used in FTF:

- `Land Survey Only`
- `Land Survey and Elevation`
- `Elevation Certificate Only`
- `Boundary Survey`
- `Topographic Survey`

Use `GET /ftf-ai-api/v1/pricing?service=<name>&tier=<tier>` to validate service names and look up pricing before creating an order.

---

## cURL Example

```bash
curl -X POST https://<host>/ftf-ai-api/v1/orders \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1042,
    "property_address": "123 Oak Street",
    "property_city": "Fort Lauderdale",
    "property_state": "FL",
    "property_zip": "33301",
    "service_type": "Land Survey Only"
  }'
```

---

## Notes

- `property_address`, `property_city`, and `property_state` are stored **uppercase** in the database (matching the convention used by the rest of the system).
- The `customer_id` must already exist — this endpoint does **not** create new customer accounts.
- Order ID is a plain integer (e.g. `10527`), not prefixed. Use it directly in subsequent calls like `GET /orders/10527` or `POST /invoices` (as `order_id`).
