import ssl
import httpx

from core.exceptions import FEMAUnavailableError
from core.logger import get_logger

logger = get_logger(__name__)

# Primary: FEMA NFHL ArcGIS REST — Special Flood Hazard Area polygons (layer 28)
_FEMA_PRIMARY = (
    "https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer/28/query"
)
# Alternate: same dataset hosted on ArcGIS Online (different SSL chain, more reliable)
_FEMA_ALTERNATE = (
    "https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/"
    "National_Flood_Hazard_Layer_NFHL/FeatureServer/28/query"
)
_TIMEOUT = 20.0


def _ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    # FEMA primary server uses legacy TLS — OP_LEGACY_SERVER_CONNECT reduces strictness
    ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0)
    return ctx


def _query_params(lat: float, lng: float) -> dict:
    return {
        "geometry":     f'{{"x":{lng},"y":{lat}}}',
        "geometryType": "esriGeometryPoint",
        "inSR":         "4326",
        "spatialRel":   "esriSpatialRelIntersects",
        "outFields":    "FLD_ZONE,ZONE_SUBTY",
        "returnGeometry": "false",
        "f":            "json",
    }


def _parse_zone(data: dict) -> str:
    features = data.get("features", [])
    if not features:
        return "X"
    return features[0].get("attributes", {}).get("FLD_ZONE") or "X"


def check_flood_zone(lat: float, lng: float) -> str:
    """Return the FEMA flood zone code for a given coordinate pair.

    Tries three strategies in order:
      1. Primary FEMA endpoint with OP_LEGACY_SERVER_CONNECT SSL context
      2. Primary FEMA endpoint with SSL verification disabled (Python 3.14 TLS compat)
      3. ArcGIS Online alternate endpoint (different SSL certificate chain)

    Returns "X" when coordinates fall outside any mapped flood zone polygon.
    Zone codes starting with A or V indicate Special Flood Hazard Areas.
    Raises FEMAUnavailableError only when all three strategies fail.
    """
    params = _query_params(lat, lng)
    last_exc: Exception | None = None

    # Strategy 1 — primary with legacy SSL context
    try:
        r = httpx.get(_FEMA_PRIMARY, params=params, timeout=_TIMEOUT, verify=_ssl_context())
        r.raise_for_status()
        return _parse_zone(r.json())
    except httpx.TimeoutException as exc:
        logger.warning("FEMA primary timeout lat=%s lng=%s", lat, lng)
        last_exc = exc
    except Exception as exc:
        logger.warning("FEMA primary failed lat=%s lng=%s: %s — trying no-verify", lat, lng, exc)
        last_exc = exc

    # Strategy 2 — primary with SSL verification disabled (handles Python 3.14 EOF)
    try:
        r = httpx.get(_FEMA_PRIMARY, params=params, timeout=_TIMEOUT, verify=False)
        r.raise_for_status()
        logger.info("FEMA primary (no-verify) succeeded lat=%s lng=%s", lat, lng)
        return _parse_zone(r.json())
    except Exception as exc:
        logger.warning("FEMA primary no-verify failed lat=%s lng=%s: %s — trying alternate", lat, lng, exc)
        last_exc = exc

    # Strategy 3 — ArcGIS Online alternate endpoint (different SSL chain)
    try:
        r = httpx.get(_FEMA_ALTERNATE, params=params, timeout=_TIMEOUT)
        r.raise_for_status()
        logger.info("FEMA alternate endpoint succeeded lat=%s lng=%s", lat, lng)
        return _parse_zone(r.json())
    except Exception as exc:
        logger.error("FEMA all strategies failed lat=%s lng=%s: %s", lat, lng, exc)
        last_exc = exc

    raise FEMAUnavailableError("FEMA API unavailable — all 3 strategies failed") from last_exc
