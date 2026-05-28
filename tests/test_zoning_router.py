"""Tests for zoning router endpoints."""

import pytest
from contextlib import ExitStack
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from backend.main import app


@pytest.fixture
def transport():
    return ASGITransport(app=app)


_TEE_MODULE = "backend.routers.zoning_checker"


def _patch_tee(overrides=None):
    """Create a context manager that patches all TEE service functions."""
    defaults = {
        "get_building_params": AsyncMock(return_value={
            "sd": [{"attributes": {"LABEL": "1.8"}}],
            "height": [{"attributes": {"LABEL": "21.0"}}],
            "coverage": [{"attributes": {"LABEL": "0.6"}}],
            "artiotita": [{"attributes": {"LABEL": "200"}}],
            "land_use": [{"attributes": {"LABEL": "Residential"}}],
            "zone_sector": [{"attributes": {"LABEL": "General Residential"}}],
            "building_system": [{"attributes": {"LABEL": "continuous"}}],
        }),
        "get_natura_zones": AsyncMock(return_value=[]),
        "get_archaeological_zones": AsyncMock(return_value=[]),
        "get_forest_map": AsyncMock(return_value=[]),
        "get_shoreline": AsyncMock(return_value=[]),
        "get_zoe_zones": AsyncMock(return_value=[]),
    }
    if overrides:
        defaults.update(overrides)

    stack = ExitStack()
    for name, mock in defaults.items():
        stack.enter_context(patch(f"{_TEE_MODULE}.{name}", new=mock))
    return stack


# ---------------------------------------------------------------------------
# Task 5.2: KAEK lookup
# ---------------------------------------------------------------------------

class TestKaekLookup:
    @pytest.mark.asyncio
    async def test_found_parcel(self, transport):
        mock_result = {
            "found": True,
            "kaek": "050461527012",
            "attributes": {"KAEK": "050461527012", "AREA": 1200},
            "centroid_lat": 37.975,
            "centroid_lon": 23.725,
        }
        with patch(f"{_TEE_MODULE}.get_kaek_parcel", new_callable=AsyncMock, return_value=mock_result):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/zoning/kaek", json={"kaek": "050461527012"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["kaek"] == "050461527012"
        assert data["lat"] is not None
        assert data["x"] is not None

    @pytest.mark.asyncio
    async def test_not_found(self, transport):
        mock_result = {"found": False, "kaek": "000000000000"}
        with patch(f"{_TEE_MODULE}.get_kaek_parcel", new_callable=AsyncMock, return_value=mock_result):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/zoning/kaek", json={"kaek": "000000000000"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is False


# ---------------------------------------------------------------------------
# Task 5.3: Full zoning check
# ---------------------------------------------------------------------------

class TestZoningCheck:
    @pytest.mark.asyncio
    async def test_check_with_wgs84(self, transport):
        with _patch_tee():
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/zoning/check", json={
                    "coord_system": "wgs84", "lat": 37.97, "lon": 23.73,
                })

        assert resp.status_code == 200
        data = resp.json()
        assert data["verdict"] in ("green", "yellow", "red")
        assert "verdict_summary" in data
        assert "disclaimer" in data

    @pytest.mark.asyncio
    async def test_check_with_egsa87(self, transport):
        with _patch_tee():
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/zoning/check", json={
                    "coord_system": "egsa87", "x": 481000, "y": 4205000,
                })

        assert resp.status_code == 200
        data = resp.json()
        assert data["verdict"] in ("green", "yellow", "red")

    @pytest.mark.asyncio
    async def test_green_verdict_no_risks(self, transport):
        with _patch_tee():
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/zoning/check", json={
                    "coord_system": "wgs84", "lat": 37.97, "lon": 23.73,
                })

        data = resp.json()
        assert data["verdict"] == "green"
        assert data["risk_flags"] == []

    @pytest.mark.asyncio
    async def test_red_verdict_with_natura(self, transport):
        with _patch_tee(overrides={
            "get_natura_zones": AsyncMock(
                return_value=[{"attributes": {"SITE_NAME": "Ymittos"}}]
            ),
        }):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/zoning/check", json={
                    "coord_system": "wgs84", "lat": 37.97, "lon": 23.73,
                })

        data = resp.json()
        assert data["verdict"] in ("yellow", "red")
        assert len(data["risk_flags"]) > 0

    @pytest.mark.asyncio
    async def test_fallback_on_tee_failure(self, transport):
        with _patch_tee(overrides={
            "get_building_params": AsyncMock(return_value={
                k: [] for k in ("sd", "height", "coverage", "artiotita", "land_use", "zone_sector", "building_system")
            }),
        }):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/zoning/check", json={
                    "coord_system": "wgs84", "lat": 37.97, "lon": 23.73,
                })

        assert resp.status_code == 200
        data = resp.json()
        assert data["verdict"] in ("green", "yellow", "red")
        assert "disclaimer" in data
        assert "Static" in data["data_source"]

    @pytest.mark.asyncio
    async def test_response_matches_schema(self, transport):
        with _patch_tee():
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/zoning/check", json={
                    "coord_system": "wgs84", "lat": 37.97, "lon": 23.73,
                })

        data = resp.json()
        required_keys = ["verdict", "verdict_summary", "zone_name", "zone_type",
                         "land_use", "municipality", "risk_flags", "building_params",
                         "regulations_summary", "data_source", "disclaimer"]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"
