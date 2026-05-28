"""Tests for TEE ArcGIS REST API service (all HTTP calls mocked)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from backend.services.tee_service import get_kaek_parcel, get_all_layers


def _mock_response(json_data, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


class TestGetKaekParcel:
    @pytest.mark.asyncio
    async def test_found_parcel_with_centroid(self):
        polygon_rings = [[[23.72, 37.97], [23.73, 37.97], [23.73, 37.98], [23.72, 37.98], [23.72, 37.97]]]
        features = [{
            "attributes": {"KAEK": "050461527012", "AREA": 1200},
            "geometry": {"rings": polygon_rings},
        }]

        with patch("backend.services.tee_service.httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.get = AsyncMock(return_value=_mock_response({"features": features}))
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await get_kaek_parcel("050461527012")

        assert result["found"] is True
        assert abs(result["centroid_lat"] - 37.975) < 0.01
        assert abs(result["centroid_lon"] - 23.725) < 0.01

    @pytest.mark.asyncio
    async def test_not_found(self):
        with patch("backend.services.tee_service.httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.get = AsyncMock(return_value=_mock_response({"features": []}))
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await get_kaek_parcel("000000000000")

        assert result["found"] is False

    @pytest.mark.asyncio
    async def test_timeout_returns_not_found(self):
        with patch("backend.services.tee_service.httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await get_kaek_parcel("050461527012")

        assert result["found"] is False


class TestGetAllLayers:
    @pytest.mark.asyncio
    async def test_returns_dict_with_all_keys(self):
        with patch("backend.services.tee_service.httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.get = AsyncMock(return_value=_mock_response({"features": []}))
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await get_all_layers(37.97, 23.73)

        assert isinstance(result, dict)
        assert "sd" in result
        assert "building_permits" in result
        assert "ypd_density" in result
        assert "survey_diagrams" in result
        assert "municipality" in result
        assert "natura" in result

    @pytest.mark.asyncio
    async def test_timeout_returns_empty_lists(self):
        with patch("backend.services.tee_service.httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await get_all_layers(37.97, 23.73)

        for key in result:
            assert result[key] == []
