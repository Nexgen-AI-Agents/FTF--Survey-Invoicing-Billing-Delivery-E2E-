# Recording 02 — Quoting & Ordering Workflow
**Source:** `Resources/Recordings from Robert/frames/02_quoting_ordering_workflow/` (835 frames @ 1 fps)
**Date recorded:** 2026-05-25
**Analyst:** Claude Code (frame-by-frame review)

---

## Executive Summary

Robert (NexGen coordinator) handles incoming survey quote requests that arrive via three channels: email (Outlook), Microsoft Teams (internal/external chat), and a web form on nexgensurveying.com. For each request he opens the FTF portal (`fieldtofinish.jobs`) and either finds an existing customer record or registers a new one. He enters the property address and looks up the parcel on the county property appraiser GIS site to confirm the county (sometimes Googling "what county is [city] in" first). He then opens an existing order or creates a new one, fills in property and customer details, generates an invoice using the **Generate Invoice** modal (selecting service type and entering qty/price), and sends the invoice + any survey files to the customer using the built-in **Deliver / Invoice** email modal. The order remains in "Quote" status in the Track Flow queue until accepted/paid.

---

## Numbered Step-by-Step Workflow

### Phase 1 — Intake (Quote Request Received)

**Step 1 — Monitor incoming channels for quote requests**
Robert has three open sources simultaneously:
- Outlook inbox (filtered to "quote" search) — receives forwarded emails from customers, agents, and title companies
- Microsoft Teams — "Blue Invoicing" channel and direct messages carry quote requests and internal discussions
- nexgensurveying.com web form — customers submit directly; appears in the FTF portal automatically

**Step 2 — Read the quote request email/message**
Robert opens the email and reads:
- Property address
- Type of survey requested (boundary, elevation certificate, land survey only, etc.)
- Any special requirements (ALTA, CAD file, specific flags)
- Customer contact info (name, phone, email, company)
- Deadline or urgency noted

Example email seen (frame 0001):
> Subject: [EXTERNAL] Re: Tuff Shed Permitting - Survey with Additional information needed - 15824 76th Tral N
> From: Freya Rodriguez <freya@CYPRESS-TITLE.com>
> Body excerpt: "...NexGen Surveying — I am requesting a quote/link to a survey on the following property: 15824 76th Trail North, Palm Beach, FL 33418 CERTIFIED TO: Troy Kuberneticus...
> The permit was denied for the following reasons: [detailed list including ALTA/NSPS requirements, existing drainage areas, flood zone, etc.]"

### Phase 2 — Customer Lookup / Registration

**Step 3 — Search for existing customer in FTF Sales Flow**
- Navigate to `fieldtofinish.jobs` → Sales Flow module
- Search by company name or email
- If found: open company/individual profile

**Step 4 — If new customer: Register New Individual or Register New Company**
- Opens modal "Register New Individual" (or Register Company variant)
- Fills in all fields (see Form Fields table below)
- Pricing defaults pre-populate (Survey, Acreage, EC, BC, BC Only)
- Saves record

### Phase 3 — Order Entry

**Step 5 — Open or create order in Track Flow**
- Navigate to `fieldtofinish.jobs/trackflow` (Track Flow module)
- Either click an existing order row (if already auto-created from web form) or create new
- URL pattern for order: `https://fieldtofinish.jobs/order?order=XXXXXXXXXX`
- URL pattern for trackflow: `https://fieldtofinish.jobs/trackflow/ftf_with_record_filter?filter=N`

**Step 6 — Fill in Order Information fields**
On the order detail page (see Form Fields table below):
- Ordered By (customer name/company auto-filled from account)
- Property Information section: address, city, state, zip, county, unit number, lot/block
- Flood/Hazard Zone (dropdown: None, FLOOD ZONE, etc.)
- Service type (Quote type field)
- External Resources links (auto-generate Google Maps, County Appraiser, Aerial Map, FEMA Flood Map, Generate links)

**Step 7 — Determine the county**
If county is not obvious from address:
- Google "what county is [city] fl in" (seen: "what county is lighthouse point fl in")
- Opens county property appraiser site to confirm parcel
- Counties observed: BROWARD COUNTY, PALM BEACH COUNTY, MARTIN COUNTY

**Step 8 — Look up parcel on County Property Appraiser GIS**
Robert visits county-specific GIS/appraiser sites:
- **Broward:** `bcpa.net` (Marty Kiar — Broward County Property Appraiser)
  - URL pattern: `https://gisweb-adapters.bcpa.net/bcpawebmap_ex/bcpawebmap.aspx?FOLIO=XXXXXXXXXX`
  - Search by address; confirms parcel ID (FOLIO), owner, situs address, legal description, values
- **Palm Beach:** `pbcgov.com` / Dorothy Jacks — Palm Beach County Property Appraiser
  - GIS map at `gis.pbcgov.org/papagis/papa.html`
  - Property Detail panel: Owner, Location, Municipality, Parcel No., Subdivision, Book/Page, Sale Date
- Uses parcel map to visually inspect lot shape/size to estimate survey complexity

**Step 9 — Enter/confirm FOLIO and county on order**
- County field on order: typed as e.g., "BROWARD COUNTY"
- FOLIO/parcel number entered in appropriate field

### Phase 4 — Generate Invoice / Quote

**Step 10 — Click "Generate Invoice" button on order**
- Opens **Generate Invoice** modal
- Pre-filled: Property Purchaser, Order Number, Order Date, Address
- Select service type from dropdown
- Enter Qty and Price
- Add additional line items with "+ Add Item"
- Fields: TOTAL, PAID, BALANCE auto-calculate
- Click OK to save

**Step 11 — Set order status to "Quote"**
- Order rating bar at top: color-coded progress bar (red→orange→yellow→green segments)
- Status set to "Quote" in dropdown (top right of order)

### Phase 5 — Send Invoice / Quote to Customer

**Step 12 — Click "Deliver / Invoice" button**
- Opens **Deliver / Invoice** modal with fields:
  - Invoice PDF (file selector — "Select Invoice PDF File")
  - Merged and Signed Survey PDF (file selector — "Select Merged and Signed Survey PDF File" / "Merged and Signed Survey PDF File [dropdown with options]")
  - Elevation Certificate (file selector — "Select Elevation Certificate PDF File")
  - Other (file selector — "Select additional PDF File")
  - Recipient(s) (pre-filled from account email, editable)
  - Subject (pre-filled, editable)
  - Message (rich text body, pre-filled template)

**Step 13 — Confirm/edit email and send**
The pre-filled message template reads (frame 0555):
> "Hello Jean,
> Your invoice for order has been generated. We are delighted to have the privilege of serving you. The delivery is for: 3721 NE 30TH AVE LIGHTHOUSE POINT FL 33064
> If this invoice has not yet been paid, please click below to make payment: [Pay Now]
> If you are any questions regarding your order, please contact us by either replying to this email or by visiting us at nexgen.enterprises. We look forward to maintaining all of your surveying...
> Note to the email delivered to the recipient(s) specified above, this message is followed by an itemized breakdown of the PDFs included in this delivery. The message is customized depending on certain factors, such as sending an invoice before or after sending the survey, depending on whether pending item(s) in the county and the invoice has been paid. Limits on payment options. Lastly, it is also a description of all of our services."

**Step 14 — Send**
- Click "Send" button
- System sends email to recipient(s) with invoice PDF attached

### Phase 6 — Post-Quote Follow-up

**Step 15 — Monitor Teams / email for customer response**
- "Blue Invoicing" Teams channel used for client communication
- Seen examples: clients asking for discounts, confirming order, providing additional info
- Seen: "Client: Please order the survey, without the elevation certificate for $416.00."
- Seen: internal note about Miguel's address not being found — manual correction needed

**Step 16 — Update order notes**
- "Office Notes" tab on order — checkboxes for:
  - Construction/Permitting
  - Commonworks/ALTA table A
  - Quote link
  - Traverse Job
- Free-text note field
- "Internal Notes" tab — for internal staff communications
- "Customer Comments" tab — visible to/from customer

**Step 17 — Order moves forward in Track Flow queue**
- Once quote accepted, status advances from "Quote" → next workflow step
- Track Flow queue shows all active orders with color-coded status rows

---

## Form Fields — Complete Table

### Register New Individual Modal

| Field | Type | Example / Notes |
|-------|------|-----------------|
| Individual First Name | Text | — |
| Individual Last Name | Text | — |
| Individual Address | Text (address lookup) | "Enter a location" placeholder |
| Individual City | Text | — |
| Individual State | Text | — |
| Individual Zipcode | Text | — |
| Individual County | Text | — |
| Individual Email | Email | e.g., aj_test@gmail.com |
| Individual Phone | Phone | — |
| Landtech | Dropdown | "No" default |
| Survey | Number | 500.00 (default seen) |
| Acreage | Number | 492.00 (default seen) |
| EC | Number | 180.00 (default seen) |
| BC Only | Number | 225.00 (default seen) |

### Order Information Page

| Field | Type / Section | Example Value Seen |
|-------|---------------|-------------------|
| Order # | Auto-generated | 364219, 364107, 284097, 284205 |
| Order Rating | Progress bar | Color-coded (red/orange/yellow/green) |
| Needed Date | Date picker | — |
| Closing Date | Date picker | — |
| Set up Complete | Checkbox (Yes/No) | — |
| Status | Dropdown (top right) | Quote, (others) |
| Ordered By — Name | Text (linked to account) | Law Offices of Jean Cascio, PLLC; Louise Folbresson |
| Ordered By — Contact | Text | Jean Cascio; Frank Alceus |
| Ordered By — Email | Email | jean@cascioandcascio.com; louise@nexgensurveying.com |
| Ordered By — Boundaries Survey Note | Text area | "Boundaries Survey No Skating Quote" |
| Property Information — Service Type | Text/label | "Q Quote"; "Land Survey Only" |
| Property Information — Address | Text | 3721 NE 30TH AVE |
| Property Information — City | Text | LIGHTHOUSE POINT |
| Property Information — State | Text | FL |
| Property Information — Zip | Text | 33064 |
| Property Information — Unit Number | Text | — |
| Property Information — County | Text | BROWARD COUNTY; PALM BEACH COUNTY; MARTIN COUNTY |
| Property Information — Lot Number | Text | — |
| Flood/Hazard Zone | Dropdown | None; FLOOD ZONE; AE |
| External Resources — Google Maps | Auto-link | Street View, Aerial Map |
| External Resources — County Appraiser | Auto-link | County Clerk |
| External Resources — FEMA | Auto-link | Generate, Elev Cert Temp |
| Lat/Long | Auto-generated coords | e.g., 26.27738951, -80.11670000066 |
| Move Order to Another Account | Button | — |
| View Company's Profile in Sales | Button | — |
| FOLIO | Text (in county parcel lookup) | 484317020560 |

### Generate Invoice Modal

| Field | Type | Example Value |
|-------|------|--------------|
| Property Purchaser | Text (auto-filled) | Jean Cascio |
| Order Number | Text (auto-filled) | 1000364219 |
| Order Date | Date (auto-filled) | 05-25-2026 |
| Address | Text (auto-filled) | 3721 NE 30TH AVE, LIGHTHOUSE POINT, FL 33064 |
| Service Type | Dropdown | Boundary Survey (selected) |
| Qty | Number | 1 |
| Price | Currency | (price field) |
| + Add Item | Button | Adds another line |
| TOTAL | Calculated | $446.00 seen |
| PAID | Calculated | $0 |
| BALANCE | Calculated | $446.00 seen |
| Notes | Text area | — |

### Deliver / Invoice Modal

| Field | Type | Notes |
|-------|------|-------|
| Invoice PDF | File selector | Select Invoice PDF File |
| Merged and Signed Survey PDF | File selector / Dropdown | Options: "Merged and Signed Survey PDF File", "Merged and Signed Survey PDF File [variant]" |
| Elevation Certificate | File selector | Select Elevation Certificate PDF File |
| Other | File selector | Select additional PDF File |
| Recipient(s) | Email (pre-filled) | From account; editable |
| Subject | Text (pre-filled) | Editable |
| Message | Rich text (pre-filled) | Template auto-populated |
| Send / Cancel | Buttons | — |

### Track Flow Queue Columns

| Column | Notes |
|--------|-------|
| (color bar) | Status color coding — red/orange/yellow/green/teal |
| Date | Order date |
| Order # | Clickable link |
| (flag icon) | Priority/flag indicator |
| Order # (repeat) | — |
| Address | Property address |
| Client | Customer name |
| Flag | Survey type or flag |
| Setup | Setup status |
| Coordinator | Assigned coordinator |
| Drafter | Assigned drafter |
| Checker | Assigned checker |
| Surveyor | Assigned surveyor |

---

## Service Types Found

| Service Type Name | Where Seen | Notes |
|-------------------|-----------|-------|
| Boundary Survey | Generate Invoice dropdown (frame 0535, 0540) | Most common type; seen selected with $446 price |
| Elevation Certificate | Generate Invoice dropdown (frame 0535) | — |
| Elevation Only | Generate Invoice dropdown (frame 0535) | Distinct from full EC |
| Acreage | Generate Invoice dropdown (frame 0535) | — |
| Land Survey Only | Order property info label (frame 0605, 0610) | Appears as order service label |
| ALTA/NSPS | Referenced in email text (frame 0001) | Special/complex survey type |
| Boundary Survey (no EC) | Referenced in Teams (frame 0680) | Client specifically excluded EC: "$416.00 without elevation certificate" |
| Commonworks/ALTA table A | Office Notes checkbox | Variant noted in order notes |
| Traverse Job | Office Notes checkbox | Internal classification |
| Construction/Permitting | Office Notes checkbox | Use case classification |

---

## Pricing Data Found

| Service | Amount | Context |
|---------|--------|---------|
| Boundary Survey | $446.00 | Generate Invoice modal (frames 0536–0540); TOTAL shown |
| Boundary Survey (no EC) | $416.00 | Teams chat — client requested survey without elevation cert |
| Survey (default rate) | $500.00 | Register New Individual modal pricing field |
| Acreage (default rate) | $492.00 | Register New Individual modal pricing field |
| EC (default rate) | $180.00 | Register New Individual modal pricing field |
| BC Only (default rate) | $225.00 | Register New Individual modal pricing field |
| PAID | $0 | At time of quote generation (not yet paid) |
| BALANCE | $446.00 | Equal to TOTAL at quote stage |

---

## County / Location Data

| County | Property Appraiser Site | GIS URL Pattern |
|--------|------------------------|----------------|
| Broward | Marty Kiar — bcpa.net | `gisweb-adapters.bcpa.net/bcpawebmap_ex/bcpawebmap.aspx?FOLIO=XXXXXXXXXX` |
| Palm Beach | Dorothy Jacks — pbcgov.com | `gis.pbcgov.org/papagis/papa.html` |
| Martin | (County Appraiser icon shown) | Not captured in detail |

Robert uses these sites to:
1. Confirm the parcel exists at the given address
2. Get the official FOLIO/parcel number
3. Visually inspect lot boundaries and size
4. Check flood zone / proximity to water (relevant for EC pricing)
5. Confirm owner name (for invoice)

---

## Order Status Values Observed

| Status | Color | Notes |
|--------|-------|-------|
| Quote | Orange (right end of bar) | Newly entered, awaiting customer acceptance |
| (Unassigned columns) | — | Coordinator/Drafter/Checker/Surveyor all blank at Quote stage |

Track Flow queue also shows rows with:
- Yellow highlight — "This address belongs to the Smith Zone" (special flag, frame 0590)
- Red rows — urgent/overdue orders
- Green rows — completed/delivered
- Teal/blue rows — in progress

---

## Decision Points (Human Judgment Required)

| # | Decision | Options | Trigger |
|---|----------|---------|---------|
| D1 | Which service type to quote | Boundary Survey, EC, ALTA, Land Survey Only, Elevation Only, Acreage, etc. | Based on customer request + property characteristics |
| D2 | What price to quote | Varies; defaults in customer record, adjusted per job | County, lot size, complexity, water adjacency |
| D3 | County lookup method | Google search → property appraiser site | Address city is ambiguous (e.g., "Lighthouse Point") |
| D4 | New vs. existing customer | Search first; register if not found | Email/name not in FTF database |
| D5 | Include Elevation Certificate | EC included or excluded | Customer request or Robert's judgment on property type |
| D6 | Flag for ALTA/complex | Check "Commonworks/ALTA table A" in notes | Email content mentions ALTA, structural, or complex requirements |
| D7 | Assign coordinator | Assign to coordinator in Track Flow | Order type / workload |
| D8 | Respond via email vs. Teams | Send formal Deliver/Invoice email OR respond in Teams chat | Depends on how request came in |
| D9 | Whether to search county parcel | Look up FOLIO or skip | Robert always checks for non-obvious properties |

---

## Special Cases / Rules Observed

1. **County determination via Google search:** Robert actively searches "what county is [city] fl in" when unsure — this is a manual friction point that automation can eliminate by mapping Florida cities → counties.

2. **BCPA "No Results" issue:** Frame 0440–0465 shows BCPA search returning "No Results matched your search criteria. Please modify your search and try again." Robert then retries with different search terms. Automation must handle BCPA search failures gracefully.

3. **Partial address on BCPA:** The address shown on BCPA for the Lighthouse Point property was "FCT NE 20 AVENUE" — different from the order address "3721 NE 30TH AVE." Robert cross-references by FOLIO number. Automation should match by FOLIO not just address string.

4. **Teams "Blue Invoicing" channel — real-time client negotiation:** Clients sometimes negotiate price or change scope in Teams chat (e.g., "without the elevation certificate for $416.00"). This is currently manual. AI pipeline needs a mechanism to flag scope changes.

5. **Yellow-highlighted row in Track Flow:** A row labeled "This address belongs to the Smith Zone" was highlighted yellow — appears to be a special territory/pricing zone. Robert noted it explicitly. This rule needs to be documented in detail.

6. **"Invoice already sent" warning in Teams:** Message seen "Invoice already sent and it can be paid half and half later" — indicates some clients are allowed split payment. This is a manual override.

7. **Miguel's address error in Teams (frame 0680):** "ZM7146 Hi Miguel address is not found for this order. Can you check thank you" — address validation failures surface in Teams. Automation should catch invalid addresses before order creation.

8. **Internal Notes contain rich operational context:** Frame 0710 showed an Internal Note reading: "QUOTE: WE NEED NEW SKETCH NEW MEASUREMENTS, HOUSE COMBINES FENCE CORNERS EVERYTHING, TAKE A LOT OF PICTURES, GET IRON DRAWN WITH PLASTIC CAPS IN HIDING CORNERS, NO FLAGS, WOOD STAKES PROGRAMMED WITH PLASTIC POINTS, ALL CORNERS MUST BE FOUND. PHOTOS OF ENTIRE PROPERTY, WRITE POINT NUMBERS ON PHOTOS AT THE CORNERS AND PICTURES OF THE TOP OF THE IRON." This level of detail must be preserved and passed to crew.

9. **"Set up Complete: Yes"** checkbox on order — must be toggled when order is fully entered. Automation should set this flag.

10. **Multiple open tabs during workflow:** Robert keeps Outlook, Track Flow, Order Information, Sales Flow Company Profile, and County Appraiser map all open simultaneously — indicating the workflow is highly context-switching. Automation should consolidate data collection into a single pass.

11. **Track Flow filter URL:** `https://fieldtofinish.jobs/trackflow/ftf_with_record_filter?filter=N` — the `filter=N` param controls which orders are shown. Filter 13 was also seen.

12. **"Quotes older than 60 days will be automatically moved to Cancelled"** — shown as a warning banner on the Track Flow page (frame 0640). AI pipeline must account for quote expiry.

---

## System / URL Reference

| System | URL | Purpose |
|--------|-----|---------|
| FTF Portal (admin) | `https://fieldtofinish.jobs/admin/` | Main CRM/order management |
| FTF Track Flow | `https://fieldtofinish.jobs/trackflow/ftf_with_record_filter?filter=N` | Order queue |
| FTF Order Detail | `https://fieldtofinish.jobs/order?order=XXXXXXXXXX` | Individual order |
| FTF Sales Flow | `https://fieldtofinish.jobs/company/XXXXXXXXXX/XXXXXXXXXX` | Company/customer profile |
| Broward County PA | `https://bcpa.net` / `gisweb-adapters.bcpa.net` | Parcel lookup + GIS map |
| Palm Beach County PA | `https://pbcgov.com` / `gis.pbcgov.org/papagis/papa.html` | Parcel lookup + GIS map |
| NexGen Website Quote Form | `https://nexgensurveying.com` (quote page) | Customer self-service quote request |
| Microsoft Outlook | `https://outlook.office365.com` | Email intake |
| Microsoft Teams | Desktop app / web | Internal comms + client chat |
| Bing / Google | Web search | County lookup, property appraiser search |

---

## Verbal Intelligence (from audio transcript)

**Source:** Robert verbal session, Recording 2 audio transcript. Confirmed 2026-05-25.

### Summit's Role in the Quoting Workflow

Robert is NOT normally the one creating or importing orders in FTF. The initial quote flow involves Summit, who:
- Posts suggested prices in Microsoft Teams channels — "Blue Invoicing" channel (standard) and "Yellow Invoicing" channel
- Suggests a price per order before Robert/Alan/Mark review it

Robert, Alan, and Mark then review Summit's suggested price, confirm or adjust it, and only then is the quote sent to the client.

### Pricing Decision Factors

Robert described the factors he weighs when confirming a suggested price:

1. **Sales history with that client** — what they've accepted before (e.g., Jean Cascio: price range $400–$700, mostly $400, last accepted was $475)
2. **Property features** — pool, seawall, canal, right-of-ways; Robert checks GIS map to see features visually before confirming price
3. **Area** — geographic location, county, local market
4. **Platted vs. unplatted** — affects survey complexity
5. **Scope of work** — what exactly is being surveyed
6. **Competitive positioning** — where NGE sits relative to competitors for this client

Robert's own summary: *"Most of the time we're just looking at features, area, if we've done work with that client in the past and then what's the scope."*

**Example — Martin Paving:** Summit suggested $900. Robert agreed — property has a canal, multiple structures, located in West Palm Beach.

**Example — Jean Cascio (title company, 82 orders):** Price range $400–$700, mostly $400. Last accepted was $475.

### The Naya Rodriguez Rejection (Out-of-Scope Services)

Robert recounted an order from Naya Rodriguez that was REJECTED because she needed drainage and engineering services. NGE does NOT do engineering. This is a hard boundary — no exceptions.

Key point for pipeline design: if an order request references engineering, drainage design, or site planning (not to be confused with Survey work), it must be flagged immediately and NOT quoted. See also "Services NGE Does NOT Do" in recording_01 verbal answers.

### Robert's Review-Before-Sending Philosophy

Robert emphasized he ALWAYS reviews every estimate before it goes out. His process:
1. Summit posts suggested price in Teams
2. Robert/Alan/Mark review — check GIS map, check client history, assess property features
3. Confirm or adjust the price
4. THEN the quote is sent

This is not a rubber-stamp — it is a deliberate review step. The AI pipeline should be designed as **suggest-then-approve**, not auto-send. Even for straightforward routine orders, Robert wants to see it before it goes to the client. This has been logged as I-043 for pipeline design discussion with Prateek/Ryan.

---

## Open Questions / Ambiguities to Resolve

| # | Question |
|---|----------|
| Q1 | What are ALL valid service types in the Generate Invoice dropdown? Only 4 were captured (Boundary Survey, Elevation Certificate, Elevation Only, Acreage). Are there more (ALTA, Topographic, etc.)? |
| Q2 | What are ALL order status values in the Track Flow system? Only "Quote" was clearly confirmed. |
| Q3 | How is pricing determined per county? Is there a pricing matrix by county + service type? The "default" pricing in Register New Individual ($500 Survey, $492 Acreage, $180 EC, $225 BC Only) — do these vary per client/county? |
| Q4 | What is the "Smith Zone" yellow flag rule? Which addresses fall into it and what pricing rule does it trigger? |
| Q5 | What triggers a row to go yellow/red/green in Track Flow — is it status, date, or a flag field? |
| Q6 | The "Landtech: No" field in Register New Individual — what does Landtech mean and when is it set to Yes? |
| Q7 | How does the web form on nexgensurveying.com auto-create orders in FTF? Is it a direct API integration? |
| Q8 | Is the FEMA Flood Map link auto-generated from address/lat-long, or does Robert manually look this up? |
| Q9 | What is the difference between "BC" and "BC Only" pricing fields in Register New Individual? |
| Q10 | The "Move Order to Another Account" and "View Company's Profile in Sales" buttons — when are these used? Are there workflow rules around account reassignment? |
| Q11 | Does the "Deliver / Invoice" modal support sending without an invoice PDF (quote-only email)? Or is a PDF always required? |
| Q12 | Is there a formal SLA for quote turnaround? The 60-day auto-cancel implies ~60 days max, but what is the target response time? |
