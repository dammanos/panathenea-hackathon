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

LAYERS_BUILDING = {
    "sd": f"{_POLEO}/20",
    "height": f"{_POLEO}/16",
    "coverage": f"{_POLEO}/18",
    "artiotita": f"{_POLEO}/17",
    "land_use": f"{_POLEO}/21",
    "zone_sector": f"{_POLEO}/14",
    "building_system": f"{_POLEO}/19",
}

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

async def get_building_params(lat: float, lon: float) -> dict:
    """Query 7 building parameter layers in parallel."""
    params = _point_query_params(lat, lon)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        tasks = [
            _query_layer(client, url, params)
            for url in LAYERS_BUILDING.values()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    out = {}
    for key, result in zip(LAYERS_BUILDING.keys(), results):
        out[key] = result if isinstance(result, list) else []
    return out


async def get_natura_zones(lat: float, lon: float, buffer_m: float = 1000) -> list:
    """Query Natura 2000 layer with buffer."""
    params = _buffer_query_params(lat, lon, buffer_m)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        return await _query_layer(client, LAYER_NATURA, params)


async def get_archaeological_zones(lat: float, lon: float, buffer_m: float = 500) -> list:
    """Query 5 archaeological sublayers in parallel, tag each with _category."""
    params = _buffer_query_params(lat, lon, buffer_m)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        tasks = [_query_layer(client, url, params) for url in LAYERS_ARCHAEOLOGICAL]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    out = []
    for category, result in zip(ARCH_CATEGORIES, results):
        if isinstance(result, list):
            for feature in result:
                feature["_category"] = category
                out.append(feature)
    return out


async def get_forest_map(lat: float, lon: float) -> list:
    """Query forest map layer (point intersect)."""
    params = _point_query_params(lat, lon)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        return await _query_layer(client, LAYER_FOREST, params)


async def get_shoreline(lat: float, lon: float, buffer_m: float = 200) -> list:
    """Query shoreline layer with buffer."""
    params = _buffer_query_params(lat, lon, buffer_m)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        return await _query_layer(client, LAYER_SHORELINE, params)


async def get_zoe_zones(lat: float, lon: float) -> list:
    """Query ZOE (out-of-plan regulation) layer."""
    params = _point_query_params(lat, lon)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        return await _query_layer(client, LAYER_ZOE, params)


async def get_kaek_parcel(kaek: str) -> dict:
    """Look up a parcel by KAEK code. Returns dict with found, centroid, attributes."""
    params = {
        "where": f"KAEK='{kaek}'",
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
