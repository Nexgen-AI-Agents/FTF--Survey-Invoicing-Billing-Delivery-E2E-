ALWAYS_FLAG_SERVICES: list[str] = [
    "ALTA Table A Survey",
    "Other Services",
]

# Bootstrapped 2026-05-25 by Competitor Analyst AI via web research of Florida market.
# Source: TEAM/research/competitive_analysis.md
# Action required: Robert/Mark to validate and expand before Sprint 3 (Human Gate).
COMPETITOR_NAMES: list[str] = [
    "Apex Surveying & Mapping",
    "Apex Surveying",
    "ApexSurvey",
    "GT Surveys",
    "GT Surveyors",
    "Land Surveying Palm Beach",
    "Florida Builders Engineers & Inspectors",
    "Accurate Land Surveyors",
    "Accurate Land Surveyors Inc",
    "Suarez Surveying & Mapping",
    "Suarez Surveying",
    "Stoner & Associates",
    "Stoner Surveyors",
    "SurvTech Solutions",
    "SurvTech",
    "No Flood Florida",
    "National Flood Experts",
    "First Choice Surveying",
    "John Ibarra & Associates",
    "Atlantic Coast Surveying",
    "GeoPoint Surveying",
    "Florida Land Surveying",
    "Target Surveying",
    "Sliger & Associates",
    "Fordco Surveying",
]

COMPETITOR_DOMAINS: list[str] = [
    "apexsurvey.us",
    "gtsurvey.com",
    "landsurveyingpalmbeach.com",
    "accuratelandsurveyors.com",
    "suarezsurveying.com",
    "stonersurveyors.com",
    "survtechsolutions.com",
    "nofloodflorida.com",
    "firstchoicesurveying.com",
    "ibarralandsurveyors.com",
    "geopointsurvey.com",
    "floridalandsurveying.com",
    "targetsurveying.com",
    "acsiweb.net",
    "cwi-assoc.com",
    "studioaeng.com",
]

# FTF service types that must never be auto-quoted — always flag for human review.
# Uses exact FTF service_type names from the 24-service list.
# Bootstrapped 2026-05-25 — Robert/Mark to validate before Sprint 3.
NEVER_AUTO_QUOTE: list[str] = [
    "Specific Purpose Survey",  # Scope varies wildly; requires human scoping call
    "Lot Split",                # County/municipality review and approval cycles
    "Wetland Delineation",      # FDEP/Army Corps/SFWMD jurisdiction; regulatory complexity
]
