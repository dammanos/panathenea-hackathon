"""Tests for TEE ArcGIS REST API service (all HTTP calls mocked)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from backend.services.tee_service import (
    get_building_params,
    get_natura_zones,
    get_archaeological_zones,
    get_forest_map,
    get_shoreline,
    get_zoe_zones,
    get_kaek_parcel,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _arcgis_response(features, geometry=None):
    """Build a mock ArcGIS JSON response."""
    data = {"features": features}
    if geometry:
        data["features"] = [{"attributes": f.get("attributes", {}), "geometry": geometry} for f in features]
    return data


def _mock_response(json_data, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# Task 4.1: Building params
# ---------------------------------------------------------------------------

class TestGetBuildingParams:
    @pytest.mark.asyncio
    async def test_parses_all_seven_layers(self):
        """Should query 7 layers in parallel and return combined results."""
        features_sd = [{"attributes": {"LABEL": "1.8"}}]
        features_height = [{"attributes": {"LABEL": "21.0"}}]
        features_coverage = [{"attributes": {"LABEL": "0.6"}}]
        features_artiotita = [{"attributes": {"LABEL": "200"}}]
        features_land_use = [{"attributes": {"LABEL": "Residential"}}]
        features_zone = [{"attributes": {"LABEL": "General Residential"}}]
        features_building_sys = [{"attributes": {"LABEL": "continuous"}}]

        responses = [
            _mock_response(_arcgis_response(features_sd)),
            _mock_response(_arcgis_response(features_height)),
            _mock_response(_arcgis_response(features_coverage)),
            _mock_response(_arcgis_response(features_artiotita)),
            _mock_response(_arcgis_response(features_land_use)),
            _mock_response(_arcgis_response(features_zone)),
            _mock_response(_arcgis_response(features_building_sys)),
        ]

        with patch("backend.services.tee_service.httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.get = AsyncMock(side_effect=responses)
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await get_building_params(37.97, 23.73)

        assert isinstance(result, dict)
        assert "sd" in result
        assert "height" in result
        assert "coverage" in result
        assert "artiotita" in result
        assert "land_use" in result
        assert "zone_sector" in result
        assert "building_system" in result

    @pytest.mark.asyncio
    async def test_empty_response_returns_empty_features(self):
        """When TEE returns no features, result should have empty lists."""
        empty = _mock_response(_arcgis_response([]))
        responses = [_mock_response(_arcgis_response([])) for _ in range(7)]

        with patch("backend.services.tee_service.httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.get = AsyncMock(side_effect=responses)
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await get_building_params(37.97, 23.73)

        for key in result:
            assert result[key] == []

    @pytest.mark.asyncio
    async def test_timeout_returns_empty(self):
        """On timeout, should return empty results gracefully."""
        with patch("backend.services.tee_service.httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await get_building_params(37.97, 23.73)

        assert isinstance(result, dict)
        for key in result:
            assert result[key] == []


# ---------------------------------------------------------------------------
# Task 4.2: Environmental & restriction layers
# ---------------------------------------------------------------------------

class TestGetNaturaZones:
    @pytest.mark.asyncio
    async def test_returns_features(self):
        features = [{"attributes": {"SITE_CODE": "GR3000006", "SITE_NAME": "Ymittos"}}]
        with patch("backend.services.tee_service.httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.get = AsyncMock(return_value=_mock_response(_arcgis_response(features)))
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await get_natura_zones(37.97, 23.73, buffer_m=1000)

        assert len(result) == 1
        assert result[0]["attributes"]["SITE_CODE"] == "GR3000006"

    @pytest.mark.asyncio
    async def test_empty_returns_empty_list(self):
        with patch("backend.services.tee_service.httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.get = AsyncMock(return_value=_mock_response(_arcgis_response([])))
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await get_natura_zones(37.97, 23.73)

        assert result == []


class TestGetArchaeologicalZones:
    @pytest.mark.asyncio
    async def test_queries_five_sublayers(self):
        """Should query 5 sublayers and tag each with _category."""
        features = [[{"attributes": {"NAME": f"site_{i}"}}] for i in range(5)]
        responses = [_mock_response(_arcgis_response(f)) for f in features]

        with patch("backend.services.tee_service.httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.get = AsyncMock(side_effect=responses)
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await get_archaeological_zones(37.97, 23.73, buffer_m=500)

        assert len(result) == 5
        for item in result:
            assert "_category" in item

    @pytest.mark.asyncio
    async def test_empty_sublayers(self):
        responses = [_mock_response(_arcgis_response([])) for _ in range(5)]

        with patch("backend.services.tee_service.httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.get = AsyncMock(side_effect=responses)
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await get_archaeological_zones(37.97, 23.73)

        assert result == []


class TestGetForestMap:
    @pytest.mark.asyncio
    async def test_returns_features(self):
        features = [{"attributes": {"TYPE": "forest"}}]
        with patch("backend.services.tee_service.httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.get = AsyncMock(return_value=_mock_response(_arcgis_response(features)))
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await get_forest_map(37.97, 23.73)

        assert len(result) == 1


class TestGetShoreline:
    @pytest.mark.asyncio
    async def test_returns_features(self):
        features = [{"attributes": {"DIST": "150"}}]
        with patch("backend.services.tee_service.httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.get = AsyncMock(return_value=_mock_response(_arcgis_response(features)))
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await get_shoreline(37.97, 23.73, buffer_m=200)

        assert len(result) == 1


class TestGetZoeZones:
    @pytest.mark.asyncio
    async def test_returns_features(self):
        features = [{"attributes": {"ZONE_NAME": "ZOE A"}}]
        with patch("backend.services.tee_service.httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.get = AsyncMock(return_value=_mock_response(_arcgis_response(features)))
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await get_zoe_zones(37.97, 23.73)

        assert len(result) == 1


class TestGetKaekParcel:
    @pytest.mark.asyncio
    async def test_found_parcel_with_centroid(self):
        """Should compute centroid from polygon rings."""
        polygon_rings = [[[23.72, 37.97], [23.73, 37.97], [23.73, 37.98], [23.72, 37.98], [23.72, 37.97]]]
        features = [{
            "attributes": {"KAEK": "050461527012", "AREA": 1200},
            "geometry": {"rings": polygon_rings},
        }]
        resp_data = {"features": features}

        with patch("backend.services.tee_service.httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.get = AsyncMock(return_value=_mock_response(resp_data))
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await get_kaek_parcel("050461527012")

        assert result is not None
        assert result["found"] is True
        assert "centroid_lat" in result
        assert "centroid_lon" in result
        # Centroid of the square should be approximately center
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

        assert result is not None
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
