"""Tests for the objective-value endpoint."""

import pytest
from httpx import AsyncClient, ASGITransport

from backend.main import app


@pytest.mark.asyncio
async def test_objective_value_endpoint_basic():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/value/objective", json={
            "zone_price": 1500.0,
            "area_m2": 100.0,
            "year_built": 2016,
            "ref_year": 2026,
            "has_frontage": True,
        })
    assert resp.status_code == 200
    body = resp.json()
    assert body["objective_value"] == 120000.0      # 1500 × 100 × 0.80
    assert body["coefficients"]["age"] == 0.80
    # Default floor coefficient should be flagged as an assumption.
    assert any("Σ.Ο." in a for a in body["assumptions"])


@pytest.mark.asyncio
async def test_objective_value_endpoint_missing_zone_price():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/value/objective", json={"area_m2": 100.0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["objective_value"] is None
    assert any("Τιμή Ζώνης" in w for w in body["warnings"])
