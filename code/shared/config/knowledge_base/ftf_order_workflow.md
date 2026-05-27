# FTF Order Workflow — AI Knowledge Base
# Source: 3 screen recordings + CREATE_ORDER_API.md
# Transcribed: 2026-05-27

## Order Entry Paths

### 1. Internal Staff ("Order Now") → PENDING status
- Staff logs into FTF portal → "Order Now" page
- Fills: property address + service(s) + date needed
- Optional: file number, agent name, contact value, access detail, parcel number,
  legal description, property type/purchaser, title company, lender company, additional details
- Submits → order created at status = **Pending** (`ng_status = 1`)
- Appears on Home Page as a Pending order immediately

### 2. Customer Website ("Order Survey") → QUOTE status
- Customer visits nexgensurveying.com → clicks "Order Survey"
- Fills the same form → submits
- Order created at status = **Quote** (called "code order" internally, `ng_status = 12`)
- Appears on Home Page under "Code Orders" tab
- **This is the input our pipeline monitors** — Agent 2 fetches status=quote orders

### 3. "Code Order" tab (internal, no service selected) → QUOTE
- Staff can also place a Quote intentionally via "Code Order" section without selecting services
- Appears as Quote in FTF with empty service_type
- Our classifier flags these (service_type="Quote" → ALWAYS_FLAG_SERVICES path)

---

## Service Types Visible in FTF Order Form (confirmed from UI recording)

These are the exact labels shown in the service dropdown in the FTF order form:

| UI Label | Canonical Name | Notes |
|---|---|---|
| Elevation Code Only | Elevation Only | Same as "Elevation Only" in pricing catalogue |
| Acreage | Acreage | In canonical list; $250 flat rate |
| Elevation Certificate | Elevation Certificate | Standard EC |
| Boundary Survey | Boundary Survey | Most common residential service |
| ALTA Survey | ALTA Table A Survey | Maps to canonical ALTA Table A Survey |
| Table Survey | UNKNOWN | Not in canonical 24-service list — I-071 |

---

## Multi-Service Orders (Child Orders) — IMPORTANT

**FTF supports multiple services per parent order.** When a customer or staff selects
"Boundary Survey + Elevation Certificate" in the form, the system creates:
- One **parent** order (the primary address/job)
- One or more **child** service entries attached to the parent

Example from recording:
  Parent order → property address
    Child 1 → Elevation Certificate
    Child 2 → Acreage

**Current pipeline limitation:** Agent 2 (monitor) returns one service_type per order
row. If FTF API returns child services as separate line items, our pipeline may only
process the first service and ignore subsequent ones → I-073.

Robert must clarify: does each child become a separate order row in the API response,
or does the parent order row contain a list of services?

---

## API Endpoint: POST /ftf-ai-api/v1/orders

**Auth:** X-API-Key header
**Required fields:** customer_id, property_address, service_type
**Optional fields:** property_city, property_state, property_zip, property_county,
                     elevation_cert (bool), notes, date_needed (YYYY-MM-DD), status

**Status on creation:**
- `status = "pending"` → ng_status = 1 (Pending)
- `status = "quote"` → ng_status = 12 (Quote)

**Response 201:** returns order_id (integer), status, customer_id, property_address,
service_type, created_at

**Known API issue (from recording):** During "How to add services" demo, narrator says
"This is an issue with the API. We need to work on it." Exact nature unclear — likely
relates to multi-service submission or date validation. Tracked as I-057 (pricing
overrides endpoint) — may be a different issue. Needs follow-up.

---

## Order Form Optional Fields (full list from recording)

| Field | Notes |
|---|---|
| File Number | For title company reference |
| Agent Name | Referring real estate agent |
| Contact Value | Agent/contact phone or email |
| Access Details | Gate codes, key info, contact on site |
| Parcel Number | County property appraiser parcel ID |
| Legal Description | From deed |
| Property Type/Purchaser | Buyer name or property classification |
| Title Company | Title/closing company name |
| Lender Company | Mortgage lender name |
| Additional Details | Free-text notes |

---

## Key Observations for AI Pipeline

1. **Quote = Code Order** — internally called "code order." Our monitor is correct to
   fetch status="quote" — these are customer-submitted website orders.

2. **Pending ≠ Quote** — internal staff orders come in as Pending, not Quote. Our
   pipeline only monitors Quotes. Staff-entered orders skip the pipeline entirely
   (they have already been manually reviewed). This is correct behavior.

3. **Date Required** — FTF UI requires a date_needed. Our API spec marks it optional
   but UI enforces it. Orders without date_needed may indicate test/malformed entries.

4. **"Elevation Code Only"** in UI = "Elevation Only" canonical → add to alias map (I-072).

5. **"Table Survey"** in UI has no confirmed mapping → flag for human (I-071).

6. **"ALTA Survey"** in UI → our classifier already maps to "ALTA Table A Survey" via
   ALWAYS_FLAG_SERVICES → correct.
