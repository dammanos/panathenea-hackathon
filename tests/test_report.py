"""Integration test for the report endpoint wiring (external calls mocked).

Verifies that the deterministic buildability is computed from the TEE layers and
returned in the response — without hitting any network or the Anthropic API.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from backend.main import app


def _layer(label):
    return [{"attributes": {"LABEL": label}}]


@pytest.mark.asyncio
async def test_report_includes_computed_buildability():
    parcel = {
        "found": True,
        "kaek": "050461527012",
        "attributes": {"AREA": "520,00"},
        "centroid_lat": 37.97,
        "centroid_lon": 23.73,
    }
    all_layers = {
        "sd": _layer("0,8"),
        "coverage": _layer("60%"),
        "height": _layer("11,00 μ."),
        "artiotita": _layer("300"),
        "city_plan_boundary": [{"attributes": {}}],
    }

    with patch("backend.routers.report.get_kaek_parcel", AsyncMock(return_value=parcel)), \
         patch("backend.routers.report.get_all_layers", AsyncMock(return_value=all_layers)), \
         patch("backend.routers.report._reverse_geocode", AsyncMock(return_value={})), \
         patch("backend.routers.report.generate_property_report",
               AsyncMock(return_value="# report")) as mock_ai:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/report/generate", json={"kaek": "050461527012"})

    assert resp.status_code == 200
    body = resp.json()
    b = body["buildability"]
    assert b is not None
    assert b["max_floor_area_m2"] == 416.0      # 0.8 * 520
    assert b["max_footprint_m2"] == 312.0       # 0.6 * 520
    assert b["indicative_max_floors"] == 3      # 11 // 3.0
    assert b["is_buildable_lot"] is True        # 520 >= 300

    # The computed result must be handed to the AI as ground-truth.
    _, kwargs = mock_ai.call_args
    assert kwargs.get("buildability") is not None
