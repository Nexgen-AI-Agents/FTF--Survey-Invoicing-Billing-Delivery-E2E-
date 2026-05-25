ALWAYS_FLAG_SERVICES: list[str] = [
    "ALTA Table A Survey",
    "Other Services",
]

# Bootstrapped 2026-05-25 by Competitor Analyst AI (web research — nexgensurveying.com + Google).
# Reviewed 2026-05-25 by Ryan AI, Robert AI, Mark AI.
# Action required: Robert/Mark to validate full list before Sprint 3 (Human Gate).
# See: TEAM/research/competitive_analysis.md for full competitor profiles.
# NOTE: "Florida Land Surveying" and "Atlantic Coast Surveying" retained but flagged as
# high-false-positive-risk entries — real Robert/Mark must confirm (see I-038).
COMPETITOR_NAMES: list[str] = [
    # Primary Florida surveying competitors (web-confirmed)
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
    "Atlantic Coast Surveying",   # Robert/Mark confirm — generic name, false positive risk (I-038)
    "GeoPoint Surveying",
    "Florida Land Surveying",     # Robert/Mark confirm — generic name, false positive risk (I-038)
    "Target Surveying",
    "Sliger & Associates",
    "Fordco Surveying",
    # National firms with active Florida presence (added after Mark AI review)
    "Terracon",
    "Terracon Consultants",
    "Kimley-Horn",
    "Kimley-Horn and Associates",
    "AECOM",
]

# NOTE: acsiweb.net — pending Robert confirmation (likely Atlantic Coast Surveying Inc).
# studioaeng.com and cwi-assoc.com removed — unconfirmed surveying firms, false positive risk.
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
    "acsiweb.net",          # Robert confirm — likely Atlantic Coast Surveying Inc (I-038)
]

# FTF service types that must never be auto-quoted — always flag for human review.
# Uses exact FTF service_type names from the 24-service list.
# Bootstrapped 2026-05-25 — expanded after Ryan AI, Robert AI, Mark AI review.
# Robert/Mark to validate complete list before Sprint 3.
NEVER_AUTO_QUOTE: list[str] = [
    "Specific Purpose Survey",  # Scope undefined until client describes purpose
    "Lot Split",                # County/municipality review and approval cycles required
    "Wetland Delineation",      # FDEP/Army Corps/SFWMD jurisdiction; outcome not guaranteed
    "B-II Title Review",        # Scope varies with title commitment exceptions; not a field job
    "Acreage",                  # $250 base rate does not hold above ~2 acres; scope swings hard
    "Legal Description",        # Metes-and-bounds / rural county descriptions not flat-rate safe
    "Topography Survey",        # $225 listed price is below FL market rate; scope varies by site
]
