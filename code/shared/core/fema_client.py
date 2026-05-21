import ssl
import httpx

from core.exceptions import FEMAUnavailableError
from core.logger import get_logger

logger = get_logger(__name__)

# FEMA National Flood Hazard Layer — Special Flood Hazard Area polygons (layer 28)
_FEMA_URL = (
    "https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer/28/query"
)
_TIMEOUT = 20.0

# FEMA ArcGIS server has legacy TLS — OP_LEGACY_SERVER_CONNECT handles UNEXPECTED_EOF
def _ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0)
    return ctx


def check_flood_zone(lat: float, lng: float) -> str:
    """
    Return the FEMA flood zone code for a given coordinate pair.

    Returns "UNAVAILABLE" only on network failure — callers must flag and escalate.
    Returns "X" when coordinates fall outside any mapped flood zone polygon.
    Zone codes starting with A or V indicate Special Flood Hazard Areas.
    """
    params = {
        "geometry": f'{{"x":{lng},"y":{lat}}}',
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "FLD_ZONE,ZONE_SUBTY",
        "returnGeometry": "false",
        "f": "json",
    }
    try:
        r = httpx.get(_FEMA_URL, params=params, timeout=_TIMEOUT, verify=_ssl_context())
        r.raise_for_status()
        data = r.json()

        features = data.get("features", [])
        if not features:
            return "X"

        zone = features[0].get("attributes", {}).get("FLD_ZONE") or "X"
        return zone
    except httpx.TimeoutException as exc:
        logger.warning("FEMA timeout for lat=%s lng=%s", lat, lng)
        raise FEMAUnavailableError("FEMA API timed out") from exc
    except Exception as exc:
        logger.error("FEMA error for lat=%s lng=%s: %s", lat, lng, exc)
        raise FEMAUnavailableError("FEMA API unavailable") from exc
