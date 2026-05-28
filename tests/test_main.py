"""Tests for FastAPI app skeleton."""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app


@pytest.fixture
def transport():
    return ASGITransport(app=app)


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, transport):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestCors:
    @pytest.mark.asyncio
    async def test_cors_headers_present(self, transport):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.options(
                "/api/health",
                headers={"Origin": "http://example.com", "Access-Control-Request-Method": "GET"},
            )
        # With allow_credentials=True, FastAPI reflects the origin rather than "*"
        assert resp.headers.get("access-control-allow-origin") in ("*", "http://example.com")
