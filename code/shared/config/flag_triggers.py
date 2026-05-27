ALWAYS_FLAG_SERVICES: list[str] = [
    "ALTA Table A Survey",
    "Other Services",
    "Building Stake Out",  # I-042/I-052: NGE status ambiguous; flag until Robert confirms back in service
    "Table Survey",        # I-071: no confirmed canonical mapping — Robert must confirm before Sprint 11
    "B-II Title Review",   # I-055: Robert (Recording 1) said human review required; overrides I-004 auto-quote decision
]

# Bootstrapped 2026-05-25 by Competitor Analyst AI (web research).
# Confirmed 2026-05-25 by Prateek (client): all names and domains validated.
# "Florida Land Surveying" confirmed competitor — floridalandsurveying.com
# "Atlantic Coast Surveying" confirmed competitor — acsiweb.net (Atlantic Coast Surveying Inc)
# 2026-05-26 by Prateek: added Exacta Land Surveyors, Me Land Services Inc, Landtec Surveying
# See: TEAM/research/competitive_analysis.md for full competitor profiles.
COMPETITOR_NAMES: list[str] = [
    # Primary Florida surveying competitors (confirmed)
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
    "Exacta Land Surveyors",
    "Exacta Land Surveyors LLC",
    "Me Land Services",
    "Me Land Services Inc",
    "Landtec Surveying",
    "Landtec Surveying and Lien",
    "Landtec Surveying and Lien LLC",
    # National firms with active Florida presence
    "Terracon",
    "Terracon Consultants",
    "Kimley-Horn",
    "Kimley-Horn and Associates",
    "AECOM",
]

# All domains confirmed 2026-05-25 by Prateek (client).
# acsiweb.net = Atlantic Coast Surveying Inc (confirmed).
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
]

# FTF service types that must never be auto-quoted — always flag for human review.
# Uses exact FTF service_type names from the 24-service list.
# Bootstrapped 2026-05-25 — expanded after Ryan AI, Robert AI, Mark AI review.
# Robert/Mark to validate complete list before Sprint 3.
# I-063: Hard rule — refund requests NEVER processed by AI.
# Any text matching these keywords triggers immediate Jessica notification and stops AI action.
REFUND_KEYWORDS: list[str] = [
    "refund", "money back", "get my money", "reimburse", "reimbursement",
    "charge back", "chargeback", "dispute charge", "reverse charge",
    "cancel and refund", "i want my money", "give me my money",
]

NEVER_AUTO_QUOTE: list[str] = [
    "Specific Purpose Survey",  # Scope undefined until client describes purpose
    "Lot Split",                # County/municipality review and approval cycles required
    "Wetland Delineation",      # FDEP/Army Corps/SFWMD jurisdiction; outcome not guaranteed
    # B-II Title Review removed 2026-05-25 — confirmed auto-quoteable by Prateek (I-004)
    # Acreage removed 2026-05-26 — flat-rate $250 routine service; Robert to confirm before Sprint 11 (I-054)
    # Legal Description removed 2026-05-26 — flat-rate $300 routine service; Robert to confirm before Sprint 11 (I-054)
    "Topography Survey",        # $225 listed price is below FL market rate; scope varies by site
]
