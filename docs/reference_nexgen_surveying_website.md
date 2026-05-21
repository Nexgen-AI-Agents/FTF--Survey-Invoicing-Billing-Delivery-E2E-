# NexGen Surveying — Website Reference

**URL:** https://nexgensurveying.com/
**Saved:** 2026-05-20
**Project:** FTF Agentic AI OS

---

## Company Info

- **Legal Name:** NexGen (Norman G. Ehlers) — operating as NexGen Land Surveying
- **Address:** 1547 Prosperity Farms Road, Lake Park, Florida 33403
- **Phone:** (561) 508-6272
- **Email:** info@nexgensurveying.com
- **Hours:** Monday–Friday, 9 AM to 5 PM (closed weekends)
- **Years in business:** Over 40 years
- **License:** Fully licensed in Florida

---

## Geographic Coverage

- **Service area: Entire state of Florida**
- Any order from outside Florida should be flagged for human review (Agent 4 — Flag Trigger #9)

---

## Services Listed on Website

| Website Name | Likely FTF Equivalent | In FTF's 24 Services? |
|---|---|---|
| Mortgage Surveys | Boundary Survey / Final Survey | Yes (likely) |
| Elevation Certificates | Elevation Certificate | Yes — exact match |
| ALTA Surveys | ALTA Table A Survey | Yes — close match |
| Geological Surveying | Unknown — possibly Other Services | NO — not in 24 services |
| Hydrographic Survey | Unknown — possibly Wetland Delineation | NO — not in 24 services |
| Land Subdivisions | Lot Split | Yes — likely |

**NOTE:** Geological Surveying and Hydrographic Survey have no direct match in FTF's 24 service names. Treat as NEVER_AUTO_QUOTE until Robert/Mark confirm.

---

## Key Personnel (from website)

- **John Pellecchia** — Principal/Owner
- **Mike** — Account Representative

---

## Legal Pages

- Privacy Policy: https://nexgensurveying.com/privacy-policy
- Terms of Use: https://nexgensurveying.com/terms-of-use
- Refund Policy: https://nexgensurveying.com/refund-policy

---

## How to Apply in the Build

| Where | Rule |
|-------|------|
| Agent 4 flag_triggers.py | `property_state != "FL"` → flag immediately (Trigger #9) |
| service_names.json | Geological + Hydrographic = unmapped → treat as Other Services (flag) until confirmed |
| Agent 9 Reporter | Use info@nexgensurveying.com and (561) 508-6272 in daily digest footer |
