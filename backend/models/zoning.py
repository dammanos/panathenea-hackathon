"""Pydantic models for zoning check requests and responses."""

from pydantic import BaseModel


class ZoningRequest(BaseModel):
    coord_system: str = "egsa87"
    lat: float | None = None
    lon: float | None = None
    x: float | None = None
    y: float | None = None
    intended_use: str = "residential"
    area_m2: float | None = None


class KaekLookupRequest(BaseModel):
    kaek: str


class KaekLookupResponse(BaseModel):
    found: bool
    kaek: str
    lat: float | None = None
    lon: float | None = None
    x: float | None = None
    y: float | None = None
    area_m2: float | None = None
    description: str = ""
    main_use: str = ""


class RiskFlag(BaseModel):
    category: str
    level: str  # high / medium / low
    title: str
    description: str


class BuildingParams(BaseModel):
    coverage_ratio: float | None = None
    building_factor: float | None = None
    max_height_m: float | None = None
    min_lot_size_m2: float | None = None
    min_frontage_m: float | None = None
    setback_front_m: float | None = None
    setback_side_m: float | None = None
    max_floors: int | None = None
    building_system: str | None = None
    fek: str | None = None
    fek_url: str | None = None


class ZoningReport(BaseModel):
    verdict: str  # green / yellow / red
    verdict_summary: str
    zone_name: str = ""
    zone_type: str = ""
    land_use: str = ""
    municipality: str = ""
    risk_flags: list[RiskFlag] = []
    building_params: BuildingParams | None = None
    regulations_summary: str = ""
    data_source: str = ""
    disclaimer: str = "Preliminary assessment. Always consult a licensed surveyor."
