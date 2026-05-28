"""Tests for Pydantic zoning models."""

import pytest
from pydantic import ValidationError
from backend.models.zoning import (
    ZoningRequest,
    KaekLookupRequest,
    KaekLookupResponse,
    RiskFlag,
    BuildingParams,
    ZoningReport,
)


class TestZoningRequest:
    def test_defaults(self):
        req = ZoningRequest()
        assert req.coord_system == "egsa87"
        assert req.intended_use == "residential"
        assert req.lat is None
        assert req.lon is None
        assert req.x is None
        assert req.y is None
        assert req.area_m2 is None

    def test_all_fields(self):
        req = ZoningRequest(
            coord_system="wgs84", lat=37.97, lon=23.73,
            x=481000.0, y=4205000.0, intended_use="commercial", area_m2=500.0,
        )
        assert req.coord_system == "wgs84"
        assert req.lat == 37.97
        assert req.area_m2 == 500.0

    def test_serialization_round_trip(self):
        req = ZoningRequest(lat=37.97, lon=23.73)
        data = req.model_dump()
        req2 = ZoningRequest(**data)
        assert req == req2


class TestKaekLookup:
    def test_request(self):
        req = KaekLookupRequest(kaek="050461527012")
        assert req.kaek == "050461527012"

    def test_response_found(self):
        resp = KaekLookupResponse(
            found=True, kaek="050461527012",
            lat=37.97, lon=23.73, x=481000.0, y=4205000.0,
            area_m2=1200.0, description="Test parcel", main_use="residential",
        )
        assert resp.found is True
        assert resp.area_m2 == 1200.0

    def test_response_not_found(self):
        resp = KaekLookupResponse(found=False, kaek="000000000000")
        assert resp.found is False
        assert resp.lat is None
        assert resp.description == ""
        assert resp.main_use == ""

    def test_response_defaults(self):
        resp = KaekLookupResponse(found=True, kaek="050461527012")
        assert resp.description == ""
        assert resp.main_use == ""
        assert resp.lat is None


class TestRiskFlag:
    def test_valid_levels(self):
        for level in ("high", "medium", "low"):
            flag = RiskFlag(category="env", level=level, title="Test", description="Desc")
            assert flag.level == level

    def test_all_fields(self):
        flag = RiskFlag(
            category="archaeological", level="high",
            title="Near Acropolis", description="Within 500m of protected site",
        )
        assert flag.category == "archaeological"
        assert flag.title == "Near Acropolis"

    def test_serialization(self):
        flag = RiskFlag(category="env", level="low", title="T", description="D")
        data = flag.model_dump()
        assert data["level"] == "low"
        flag2 = RiskFlag(**data)
        assert flag == flag2


class TestBuildingParams:
    def test_all_optional(self):
        bp = BuildingParams()
        assert bp.coverage_ratio is None
        assert bp.building_factor is None
        assert bp.max_height_m is None
        assert bp.min_lot_size_m2 is None
        assert bp.min_frontage_m is None
        assert bp.setback_front_m is None
        assert bp.setback_side_m is None
        assert bp.max_floors is None
        assert bp.building_system is None
        assert bp.fek is None
        assert bp.fek_url is None

    def test_partial_fields(self):
        bp = BuildingParams(coverage_ratio=0.6, max_height_m=21.0, max_floors=7)
        assert bp.coverage_ratio == 0.6
        assert bp.max_height_m == 21.0
        assert bp.max_floors == 7
        assert bp.building_factor is None

    def test_full_fields(self):
        bp = BuildingParams(
            coverage_ratio=0.7, building_factor=2.4, max_height_m=32.0,
            min_lot_size_m2=200.0, min_frontage_m=10.0,
            setback_front_m=3.0, setback_side_m=2.5, max_floors=10,
            building_system="continuous", fek="123/A/2020", fek_url="https://example.com",
        )
        assert bp.fek == "123/A/2020"


class TestZoningReport:
    def test_minimal(self):
        report = ZoningReport(verdict="green", verdict_summary="All clear")
        assert report.verdict == "green"
        assert report.zone_name == ""
        assert report.risk_flags == []
        assert report.building_params is None
        assert report.disclaimer == "Preliminary assessment. Always consult a licensed surveyor."

    def test_verdict_values(self):
        for v in ("green", "yellow", "red"):
            report = ZoningReport(verdict=v, verdict_summary="Test")
            assert report.verdict == v

    def test_with_risk_flags(self):
        flags = [
            RiskFlag(category="env", level="high", title="Natura", description="In Natura zone"),
            RiskFlag(category="arch", level="medium", title="Near site", description="500m"),
        ]
        report = ZoningReport(verdict="red", verdict_summary="Issues found", risk_flags=flags)
        assert len(report.risk_flags) == 2
        assert report.risk_flags[0].level == "high"

    def test_with_building_params(self):
        bp = BuildingParams(coverage_ratio=0.6, building_factor=1.8)
        report = ZoningReport(
            verdict="green", verdict_summary="OK",
            building_params=bp, zone_name="General Residential",
        )
        assert report.building_params.coverage_ratio == 0.6
        assert report.zone_name == "General Residential"

    def test_full_report(self):
        report = ZoningReport(
            verdict="yellow", verdict_summary="Minor concerns",
            zone_name="Mixed Use", zone_type="urban", land_use="commercial",
            municipality="Athens",
            risk_flags=[RiskFlag(category="x", level="low", title="T", description="D")],
            building_params=BuildingParams(max_height_m=24.0),
            regulations_summary="Standard regulations apply",
            data_source="TEE UDM",
        )
        assert report.municipality == "Athens"
        assert report.regulations_summary == "Standard regulations apply"
        assert report.data_source == "TEE UDM"

    def test_default_disclaimer(self):
        report = ZoningReport(verdict="green", verdict_summary="OK")
        assert "licensed surveyor" in report.disclaimer

    def test_custom_disclaimer(self):
        report = ZoningReport(
            verdict="green", verdict_summary="OK",
            disclaimer="Custom disclaimer",
        )
        assert report.disclaimer == "Custom disclaimer"
