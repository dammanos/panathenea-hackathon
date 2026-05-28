"""ArcGIS REST API client for TEE's Unified Digital Map (UDM)."""

import asyncio
import httpx

# ---------------------------------------------------------------------------
# Base URLs
# ---------------------------------------------------------------------------
UDM_BASE = "https://sdigmap.tee.gov.gr/mapping/rest/services/UDM"
KAEK_BASE = (
    "https://services-eu1.arcgis.com/40tFGWzosjaLJpmn/ArcGIS/rest/services"
    "/GEOTEMAXIA_LEITOURGOUN_ON_gdb/FeatureServer/0"
)

# ---------------------------------------------------------------------------
# Layer paths (under UDM_SERVICE_POLEODOMIKI_PLIROFORIA/MapServer)
# ---------------------------------------------------------------------------
_POLEO = f"{UDM_BASE}/UDM_SERVICE_POLEODOMIKI_PLIROFORIA/MapServer"

LAYER_NATURA = f"{UDM_BASE}/UDM_SERVICE_NATURA_DASIKA/MapServer/0"
LAYER_FOREST = f"{UDM_BASE}/UDM_SERVICE_NATURA_DASIKA/MapServer/15"
LAYER_SHORELINE = f"{_POLEO}/1"

LAYERS_ARCHAEOLOGICAL = [
    f"{UDM_BASE}/UDM_SERVICE_ARCHAIOLOGIKO/MapServer/{i}"
    for i in (3, 7, 11, 15, 18)
]
ARCH_CATEGORIES = [
    "declared_archaeological",
    "buffer_zone",
    "historical_site",
    "traditional_settlement",
    "other_protection",
]

LAYER_ZOE = f"{UDM_BASE}/UDM_SERVICE_RYTHMISEIS_EXOASTIKOU_CHOROU/MapServer/1"

# Additional layers for comprehensive report
_EXOAST = f"{UDM_BASE}/UDM_SERVICE_RYTHMISEIS_EXOASTIKOU_CHOROU/MapServer"
_ELSTAT = f"{UDM_BASE}/UDM_SERVICE_ELSTAT/MapServer"
_RYM = f"{UDM_BASE}/UDM_SERVICE_POLEOD_RYM_SXD/MapServer"

# High-value data layers
_PERMITS = f"{UDM_BASE}/UDM_SERVICE_OIKOODOMIKES_ADEIES_2011_2018/MapServer"
_YPD = f"{UDM_BASE}/UDM_SERVICE_YPD/MapServer"
_FEK_DOCS = f"{UDM_BASE}/UDM_SERVICE_FEK_NO_SXEDIA_DOCS/MapServer"
_SXEDIA_DOCS = f"{UDM_BASE}/UDM_SERVICE_SXEDIA_DOCS/MapServer"

LAYER_BUILDING_PERMITS = f"{_PERMITS}/12"        # Οικοδομικές Άδειες 2011-2018
LAYER_YPD_BLOCKS = f"{_YPD}/6"                   # Οικοδομικά Τετράγωνα (FEK decrees)
LAYER_YPD_DENSITY = f"{_YPD}/20"                 # Συντελεστής Δόμησης (Σ.Δ.)
LAYER_YPD_SETTLEMENT = f"{_YPD}/3"               # Όριο Οικισμού (YPD)
LAYER_FEK_DOCUMENTS = f"{_FEK_DOCS}/0"           # FEK Documents with PDF URLs
LAYER_SURVEY_DIAGRAMS = f"{_SXEDIA_DOCS}/0"       # Georeferenced survey diagrams

LAYER_PROTECTED_BUILDINGS = f"{_POLEO}/2"      # Διατηρητέα Κτίσματα
LAYER_SETTLEMENT_BOUNDARY = f"{_POLEO}/3"      # Καθορισμένο Όριο Οικισμού
LAYER_STREAMS = f"{_POLEO}/7"                  # Οριοθετημένο Ρέμα
LAYER_OUTSIDE_PLAN = f"{_POLEO}/9"             # Περιοχή Εκτός Σχεδίου
LAYER_LAND_USE_GPS = f"{_POLEO}/26"            # Χρήσεις Γης ΓΠΣ
LAYER_PUBLIC_SPACES = f"{_POLEO}/22"           # Κοινόχρηστοι/Κοινωφελείς
LAYER_ARCH_ZONE_POLEO = f"{_POLEO}/23"         # Ζώνη Αρχαιολογική (overlay)
LAYER_EXPROPRIATION = f"{_POLEO}/24"           # Ζώνη Απαλλοτρίωσης
LAYER_PD_PROTECTION = f"{_EXOAST}/2"           # ΠΔ Προστασίας zones
LAYER_ENV_STREAMS = f"{_EXOAST}/5"             # Ρέματα Περιβαλλ. Ενδιαφ.
LAYER_CITY_PLAN_BOUNDARY = f"{_RYM}/0"         # Όριο εγκεκριμ. σχεδίου
LAYER_MUNICIPALITY = f"{_ELSTAT}/0"            # Καλλικρατικοί Δήμοι 2021

TIMEOUT = 15.0


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def _point_query_params(lat: float, lon: float) -> dict:
    return {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json",
    }


def _buffer_query_params(lat: float, lon: float, buffer_m: float) -> dict:
    params = _point_query_params(lat, lon)
    params["distance"] = str(buffer_m)
    params["units"] = "esriSRUnit_Meter"
    return params


async def _query_layer(client: httpx.AsyncClient, url: str, params: dict) -> list:
    """Query a single ArcGIS layer, return features list."""
    try:
        resp = await client.get(f"{url}/query", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("features", [])
    except (httpx.TimeoutException, httpx.HTTPStatusError, Exception):
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_all_layers(lat: float, lon: float) -> dict:
    """Query ALL available TEE layers in parallel for a comprehensive report."""
    point = _point_query_params(lat, lon)
    buf200 = _buffer_query_params(lat, lon, 200)
    buf500 = _buffer_query_params(lat, lon, 500)
    buf1000 = _buffer_query_params(lat, lon, 1000)

    layer_queries = {
        # Building params (point)
        "sd": (_POLEO + "/20", point),
        "height": (_POLEO + "/16", point),
        "coverage": (_POLEO + "/18", point),
        "artiotita": (_POLEO + "/17", point),
        "land_use": (_POLEO + "/21", point),
        "zone_sector": (_POLEO + "/14", point),
        "building_system": (_POLEO + "/19", point),
        "land_use_gps": (LAYER_LAND_USE_GPS, point),
        # Plan status (point)
        "settlement_boundary": (LAYER_SETTLEMENT_BOUNDARY, point),
        "outside_plan": (LAYER_OUTSIDE_PLAN, point),
        "city_plan_boundary": (LAYER_CITY_PLAN_BOUNDARY, point),
        "public_spaces": (LAYER_PUBLIC_SPACES, point),
        # Restrictions (point)
        "expropriation": (LAYER_EXPROPRIATION, point),
        "arch_zone_poleo": (LAYER_ARCH_ZONE_POLEO, point),
        "forest": (LAYER_FOREST, point),
        # Restrictions (buffer)
        "natura": (LAYER_NATURA, buf1000),
        "shoreline": (LAYER_SHORELINE, buf200),
        "zoe": (LAYER_ZOE, point),
        "pd_protection": (LAYER_PD_PROTECTION, point),
        "streams": (LAYER_STREAMS, buf200),
        "env_streams": (LAYER_ENV_STREAMS, buf200),
        "protected_buildings": (LAYER_PROTECTED_BUILDINGS, buf200),
        "municipality": (LAYER_MUNICIPALITY, point),
        # High-value data layers
        "building_permits": (LAYER_BUILDING_PERMITS, buf500),
        "ypd_blocks": (LAYER_YPD_BLOCKS, point),
        "ypd_density": (LAYER_YPD_DENSITY, point),
        "ypd_settlement": (LAYER_YPD_SETTLEMENT, point),
        "fek_documents": (LAYER_FEK_DOCUMENTS, buf500),
        "survey_diagrams": (LAYER_SURVEY_DIAGRAMS, buf500),
    }

    # Add archaeological layers
    for i, (url, cat) in enumerate(zip(LAYERS_ARCHAEOLOGICAL, ARCH_CATEGORIES)):
        layer_queries[f"arch_{cat}"] = (url, buf500)

    keys = list(layer_queries.keys())
    urls_params = list(layer_queries.values())

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        tasks = [_query_layer(client, url, params) for url, params in urls_params]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    out = {}
    for key, result in zip(keys, results):
        out[key] = result if isinstance(result, list) else []
    return out


async def get_kaek_parcel(kaek: str) -> dict:
    """Look up a parcel by KAEK code. Returns dict with found, centroid, attributes."""
    # KAEK codes are 12-digit numeric strings — reject anything else
    clean = kaek.strip()
    if not clean.isdigit() or len(clean) != 12:
        return {"found": False, "kaek": kaek}
    params = {
        "where": f"KAEK='{clean}'",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{KAEK_BASE}/query", params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.TimeoutException, httpx.HTTPStatusError, Exception):
        return {"found": False, "kaek": kaek}

    features = data.get("features", [])
    if not features:
        return {"found": False, "kaek": kaek}

    feature = features[0]
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry", {})

    # Compute centroid from polygon rings
    centroid_lat, centroid_lon = None, None
    rings = geometry.get("rings", [])
    if rings:
        ring = rings[0]
        # Exclude closing point if it duplicates first
        pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
        if pts:
            centroid_lon = sum(p[0] for p in pts) / len(pts)
            centroid_lat = sum(p[1] for p in pts) / len(pts)

    return {
        "found": True,
        "kaek": kaek,
        "attributes": attrs,
        "centroid_lat": centroid_lat,
        "centroid_lon": centroid_lon,
    }
