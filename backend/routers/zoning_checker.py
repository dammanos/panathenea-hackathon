"""Zoning check router - KAEK lookup and full zoning check."""

import json
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter

from backend.models.zoning import (
    ZoningRequest,
    KaekLookupRequest,
    KaekLookupResponse,
    RiskFlag,
    BuildingParams,
    ZoningReport,
)
from backend.services.coordinate_converter import egsa87_to_wgs84, wgs84_to_egsa87
from backend.services.tee_service import (
    get_building_params,
    get_natura_zones,
    get_archaeological_zones,
    get_forest_map,
    get_shoreline,
    get_zoe_zones,
    get_kaek_parcel,
)

router = APIRouter(prefix="/api/v1/zoning", tags=["zoning"])

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def _load_static_rules() -> list[dict]:
    with open(DATA_DIR / "zoning_rules.json") as f:
        return json.load(f)


_FEK_FIELD_NAMES = {"FEK", "FEK_NO", "NOMOS_FEK", "ΦΕΚ", "FEK_NUMBER", "FEK_AR", "ARITHMOS_FEK"}

_FEK_SERIES_MAP = {"Α": "01", "Β": "02", "Γ": "03", "Δ": "04", "A": "01", "B": "02"}
_ET_BLOB = "https://ia37rg02wpsa01.blob.core.windows.net/fek"


def _build_fek_url(fek: str) -> str:
    """Build a direct PDF URL for a FEK reference on the ET.GR blob storage.

    Expected formats: "ΦΕΚ 166/Δ/1987", "166/Δ/1987", "ΦΕΚ 340/Β/1988".
    Falls back to search page if parsing fails.
    """
    import re
    m = re.search(r'(\d+)\s*/\s*([A-ZΑ-Ω]+)\s*/\s*(\d{4})', fek)
    if m:
        num, series, year = m.group(1), m.group(2), m.group(3)
        series_code = _FEK_SERIES_MAP.get(series)
        if series_code:
            fek_name = f"{year}{series_code}{num.zfill(5)}"
            return f"{_ET_BLOB}/{series_code}/{year}/{fek_name}.pdf"
    return f"https://search.et.gr/el/?q={quote(fek)}"


def _extract_fek(building_raw: dict) -> tuple[str | None, str | None]:
    """Scan all building param layers for FEK-related attributes."""
    for layer_features in building_raw.values():
        if not isinstance(layer_features, list):
            continue
        for feat in layer_features:
            attrs = feat.get("attributes", {})
            for key, val in attrs.items():
                if key.upper() in _FEK_FIELD_NAMES and val:
                    fek = str(val).strip()
                    if fek:
                        fek_url = _build_fek_url(fek)
                        return fek, fek_url
    return None, None


def _extract_label(features: list) -> str | None:
    """Extract LABEL from first feature's attributes."""
    if features and isinstance(features, list) and len(features) > 0:
        attrs = features[0].get("attributes", {})
        return attrs.get("LABEL") or attrs.get("label")
    return None


def _try_float(val: str | None) -> float | None:
    if val is None:
        return None
    try:
        return float(val.replace(",", "."))
    except (ValueError, AttributeError):
        return None


def _build_risk_flags(natura, archaeological, forest, shoreline, zoe) -> list[RiskFlag]:
    """Generate risk flags from environmental/restriction layer results."""
    flags = []

    for feat in natura:
        attrs = feat.get("attributes", {})
        name = attrs.get("SITE_NAME") or attrs.get("SITENAME") or "Natura 2000 zone"
        flags.append(RiskFlag(
            category="natura2000",
            level="high",
            title=f"Natura 2000: {name}",
            description=f"Property is within or near Natura 2000 protected area: {name}.",
        ))

    for feat in archaeological:
        attrs = feat.get("attributes", {})
        name = attrs.get("NAME") or attrs.get("ONOMASIA") or "Archaeological zone"
        cat = feat.get("_category", "archaeological")
        flags.append(RiskFlag(
            category="archaeological",
            level="high" if cat in ("declared_archaeological", "buffer_zone") else "medium",
            title=f"Archaeological: {name}",
            description=f"Property is within or near archaeological zone ({cat}): {name}.",
        ))

    for feat in forest:
        attrs = feat.get("attributes", {})
        flags.append(RiskFlag(
            category="forest",
            level="high",
            title="Forest map overlap",
            description="Property overlaps with an area designated in the forest map.",
        ))

    for feat in shoreline:
        attrs = feat.get("attributes", {})
        flags.append(RiskFlag(
            category="shoreline",
            level="medium",
            title="Near shoreline",
            description="Property is within the shoreline buffer zone.",
        ))

    for feat in zoe:
        attrs = feat.get("attributes", {})
        zone_name = attrs.get("LABEL") or attrs.get("ZONE_NAME") or "ZOE"
        flags.append(RiskFlag(
            category="zoe",
            level="medium",
            title=f"ZOE regulation: {zone_name}",
            description=f"Property is within a ZOE (out-of-plan regulation) zone: {zone_name}.",
        ))

    return flags


def _compute_verdict(flags: list[RiskFlag]) -> tuple[str, str]:
    """Compute verdict color and summary from risk flags."""
    if not flags:
        return "green", "No significant restrictions found. Development appears feasible."

    levels = [f.level for f in flags]
    if "high" in levels:
        return "red", f"Significant restrictions found ({len(flags)} issue(s)). Development may be restricted."
    return "yellow", f"Minor concerns found ({len(flags)} issue(s)). Further investigation recommended."


def _fallback_building_params(intended_use: str) -> BuildingParams | None:
    """Look up building params from static zoning rules as fallback."""
    rules = _load_static_rules()
    use_map = {
        "residential": "General Residential",
        "commercial": "Commercial",
        "industrial": "Industrial",
        "agricultural": "Outside Plan Agricultural",
        "tourism": "Tourism",
    }
    target = use_map.get(intended_use, "General Residential")
    for rule in rules:
        if rule["name"] == target:
            return BuildingParams(
                coverage_ratio=rule["coverage_ratio"],
                building_factor=rule["building_factor"],
                max_height_m=rule["max_height_m"],
                min_lot_size_m2=rule["min_lot_size_m2"],
                min_frontage_m=rule.get("min_frontage_m"),
                setback_front_m=rule.get("setback_front_m"),
                setback_side_m=rule.get("setback_side_m"),
                max_floors=rule.get("max_floors"),
                fek=rule.get("fek"),
                fek_url=_build_fek_url(rule["fek"]) if rule.get("fek") else None,
            )
    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/kaek", response_model=KaekLookupResponse)
async def kaek_lookup(req: KaekLookupRequest):
    result = await get_kaek_parcel(req.kaek)

    if not result.get("found"):
        return KaekLookupResponse(found=False, kaek=req.kaek)

    clat = result.get("centroid_lat")
    clon = result.get("centroid_lon")
    x, y = None, None
    if clat is not None and clon is not None:
        x, y = wgs84_to_egsa87(clat, clon)

    attrs = result.get("attributes", {})
    return KaekLookupResponse(
        found=True,
        kaek=req.kaek,
        lat=clat,
        lon=clon,
        x=x,
        y=y,
        area_m2=_try_float(str(attrs.get("AREA", ""))) if attrs.get("AREA") else None,
        description=str(attrs.get("DESCRIPTION", "")),
        main_use=str(attrs.get("MAIN_USE", "")),
    )


@router.post("/check", response_model=ZoningReport)
async def zoning_check(req: ZoningRequest):
    # Resolve coordinates to WGS84
    if req.coord_system == "egsa87" and req.x is not None and req.y is not None:
        lat, lon = egsa87_to_wgs84(req.x, req.y)
    elif req.lat is not None and req.lon is not None:
        lat, lon = req.lat, req.lon
    else:
        return ZoningReport(
            verdict="red",
            verdict_summary="No valid coordinates provided.",
        )

    # Query all TEE layers in parallel
    import asyncio
    building_raw, natura, archaeological, forest, shoreline, zoe = await asyncio.gather(
        get_building_params(lat, lon),
        get_natura_zones(lat, lon),
        get_archaeological_zones(lat, lon),
        get_forest_map(lat, lon),
        get_shoreline(lat, lon),
        get_zoe_zones(lat, lon),
    )

    # Build risk flags
    risk_flags = _build_risk_flags(natura, archaeological, forest, shoreline, zoe)
    verdict, verdict_summary = _compute_verdict(risk_flags)

    # Extract building params from TEE data
    sd_val = _try_float(_extract_label(building_raw.get("sd", [])))
    height_val = _try_float(_extract_label(building_raw.get("height", [])))
    coverage_val = _try_float(_extract_label(building_raw.get("coverage", [])))
    artiotita_val = _try_float(_extract_label(building_raw.get("artiotita", [])))
    land_use_label = _extract_label(building_raw.get("land_use", []))
    zone_label = _extract_label(building_raw.get("zone_sector", []))
    building_sys_label = _extract_label(building_raw.get("building_system", []))

    has_tee_data = any(v is not None for v in [sd_val, height_val, coverage_val])

    fek, fek_url = _extract_fek(building_raw)

    if has_tee_data:
        building_params = BuildingParams(
            coverage_ratio=coverage_val,
            building_factor=sd_val,
            max_height_m=height_val,
            min_lot_size_m2=artiotita_val,
            building_system=building_sys_label,
            fek=fek,
            fek_url=fek_url,
        )
        data_source = "TEE Unified Digital Map (live)"
    else:
        building_params = _fallback_building_params(req.intended_use)
        data_source = "Static zoning rules (TEE data unavailable)"

    # Build regulations summary
    parts = []
    if zone_label:
        parts.append(f"Zone: {zone_label}")
    if land_use_label:
        parts.append(f"Land use: {land_use_label}")
    if building_params and building_params.coverage_ratio:
        parts.append(f"Coverage: {building_params.coverage_ratio}")
    if building_params and building_params.building_factor:
        parts.append(f"Building factor: {building_params.building_factor}")
    if building_params and building_params.max_height_m:
        parts.append(f"Max height: {building_params.max_height_m}m")
    regulations_summary = ". ".join(parts) + "." if parts else ""

    return ZoningReport(
        verdict=verdict,
        verdict_summary=verdict_summary,
        zone_name=zone_label or "",
        zone_type="urban" if has_tee_data else "unknown",
        land_use=land_use_label or req.intended_use,
        municipality="",
        risk_flags=risk_flags,
        building_params=building_params,
        regulations_summary=regulations_summary,
        data_source=data_source,
    )
