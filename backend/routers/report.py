"""Property due diligence report generation."""

import asyncio
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.coordinate_converter import wgs84_to_egsa87
from backend.services.tee_service import get_all_layers, get_kaek_parcel
from backend.services.ai_report import generate_property_report


async def _reverse_geocode(lat: float, lon: float) -> dict:
    """Reverse geocode via Nominatim, return address fields."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "lat": str(lat),
                    "lon": str(lon),
                    "format": "jsonv2",
                    "accept-language": "el",
                    "addressdetails": "1",
                },
                headers={"User-Agent": "TopoTools/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return {}
    addr = data.get("address", {})
    return {
        "display_name": data.get("display_name", ""),
        "road": addr.get("road", ""),
        "house_number": addr.get("house_number", ""),
        "suburb": addr.get("suburb") or addr.get("neighbourhood", ""),
        "city": addr.get("city") or addr.get("town") or addr.get("village", ""),
        "municipality": addr.get("municipality", ""),
        "county": addr.get("county", ""),
        "postcode": addr.get("postcode", ""),
    }

router = APIRouter(prefix="/api/v1/report", tags=["report"])


class ReportRequest(BaseModel):
    kaek: str


class ReportResponse(BaseModel):
    kaek: str
    lat: float | None = None
    lon: float | None = None
    x: float | None = None
    y: float | None = None
    area_m2: float | None = None
    report_md: str = ""
    has_restrictions: bool = False
    layers_queried: int = 0
    municipality: str = ""
    address: str = ""
    postal_code: str = ""


@router.post("/generate", response_model=ReportResponse)
async def generate_report(req: ReportRequest):
    # 1. Validate and look up parcel by KAEK
    kaek = req.kaek.strip()
    if not kaek.isdigit() or len(kaek) != 12:
        raise HTTPException(status_code=400, detail="KAEK must be a 12-digit code")
    parcel = await get_kaek_parcel(kaek)
    if not parcel.get("found"):
        raise HTTPException(status_code=404, detail="Parcel not found for KAEK: " + req.kaek)

    lat = parcel.get("centroid_lat")
    lon = parcel.get("centroid_lon")
    if lat is None or lon is None:
        raise HTTPException(status_code=422, detail="Could not determine parcel coordinates")

    x, y = wgs84_to_egsa87(lat, lon)
    attrs = parcel.get("attributes", {})
    area_raw = attrs.get("AREA")
    area_m2 = None
    if area_raw:
        try:
            area_m2 = float(str(area_raw).replace(",", "."))
        except ValueError:
            pass

    # 2. Query ALL TEE layers + Nominatim in parallel
    all_layers, address_data = await asyncio.gather(
        get_all_layers(lat, lon),
        _reverse_geocode(lat, lon),
    )

    layers_queried = len(all_layers)

    # Determine restrictions
    restriction_keys = [
        "natura", "forest", "shoreline", "zoe", "pd_protection",
        "streams", "env_streams", "expropriation", "protected_buildings",
        "arch_zone_poleo",
    ]
    arch_keys = [k for k in all_layers if k.startswith("arch_")]
    restriction_keys.extend(arch_keys)
    has_restrictions = any(bool(all_layers.get(k)) for k in restriction_keys)

    # Extract municipality
    municipality = ""
    muni_features = all_layers.get("municipality", [])
    if muni_features:
        muni_attrs = muni_features[0].get("attributes", {})
        municipality = muni_attrs.get("NAME") or muni_attrs.get("LEKTIKO") or ""

    # Extract address fields
    address_str = address_data.get("display_name", "")
    postal_code = address_data.get("postcode", "")

    # 3. Generate AI report
    kaek_info = {
        "kaek": req.kaek,
        "lat": lat,
        "lon": lon,
        "x": x,
        "y": y,
        "area_m2": area_m2,
        "cadastre_attrs": attrs,
        "address": address_data,
    }

    report_md = await generate_property_report(all_layers, kaek_info)

    return ReportResponse(
        kaek=req.kaek,
        lat=lat,
        lon=lon,
        x=x,
        y=y,
        area_m2=area_m2,
        report_md=report_md,
        has_restrictions=has_restrictions,
        layers_queried=layers_queried,
        municipality=municipality,
        address=address_str,
        postal_code=postal_code,
    )
