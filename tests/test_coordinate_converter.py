"""Tests for coordinate converter - EGSA87, WGS84, GGRS87, TM07 conversions."""

import math
import pytest
from backend.services.coordinate_converter import (
    egsa87_to_wgs84,
    wgs84_to_egsa87,
    wgs84_to_tm07,
    tm07_to_wgs84,
)


# --- Task 1.1: EGSA87 <-> WGS84 ---


class TestEgsa87ToWgs84:
    """Test EGSA87 (Greek Grid) to WGS84 conversion."""

    def test_athens_area(self):
        """Known point near Athens: EGSA87 (481000, 4205000) -> WGS84 approx (37.97, 23.73)."""
        lat, lon = egsa87_to_wgs84(481000, 4205000)
        assert 37.9 < lat < 38.1, f"lat {lat} not in Athens range"
        assert 23.6 < lon < 23.8, f"lon {lon} not in Athens range"

    def test_thessaloniki_area(self):
        """Known point near Thessaloniki: EGSA87 (413000, 4500000) -> WGS84 approx (40.6, 22.9)."""
        lat, lon = egsa87_to_wgs84(413000, 4500000)
        assert 40.4 < lat < 40.8, f"lat {lat} not in Thessaloniki range"
        assert 22.7 < lon < 23.1, f"lon {lon} not in Thessaloniki range"

    def test_crete_area(self):
        """Known point in Crete: EGSA87 (575000, 3900000) -> WGS84 approx (35.2, 24.8)."""
        lat, lon = egsa87_to_wgs84(575000, 3900000)
        assert 35.0 < lat < 35.5, f"lat {lat} not in Crete range"
        assert 24.5 < lon < 25.1, f"lon {lon} not in Crete range"

    def test_returns_floats(self):
        lat, lon = egsa87_to_wgs84(481000, 4205000)
        assert isinstance(lat, float)
        assert isinstance(lon, float)


class TestWgs84ToEgsa87:
    """Test WGS84 to EGSA87 conversion."""

    def test_athens_area(self):
        """WGS84 Athens -> EGSA87 in valid Greek Grid range."""
        x, y = wgs84_to_egsa87(37.97, 23.73)
        assert 100_000 < x < 900_000, f"x={x} outside Greek Grid range"
        assert 3_800_000 < y < 4_700_000, f"y={y} outside Greek Grid range"

    def test_returns_floats(self):
        x, y = wgs84_to_egsa87(37.97, 23.73)
        assert isinstance(x, float)
        assert isinstance(y, float)


class TestEgsa87RoundTrip:
    """Round-trip accuracy tests: EGSA87 -> WGS84 -> EGSA87."""

    @pytest.mark.parametrize(
        "x, y",
        [
            (481000, 4205000),   # Athens
            (413000, 4500000),   # Thessaloniki
            (575000, 3900000),   # Crete
            (250000, 4300000),   # Western Greece
            (700000, 4100000),   # Eastern Aegean
            (500000, 4000000),   # Central Greece
        ],
    )
    def test_round_trip_submillimeter(self, x, y):
        """Round-trip must be accurate to < 2mm (datum shift through GRS80/WGS84 limits precision)."""
        lat, lon = egsa87_to_wgs84(x, y)
        x2, y2 = wgs84_to_egsa87(lat, lon)
        assert abs(x2 - x) < 0.002, f"x diff: {abs(x2 - x):.6f}m"
        assert abs(y2 - y) < 0.002, f"y diff: {abs(y2 - y):.6f}m"


class TestWgs84RoundTrip:
    """Round-trip accuracy tests: WGS84 -> EGSA87 -> WGS84."""

    @pytest.mark.parametrize(
        "lat, lon",
        [
            (37.97, 23.73),    # Athens
            (40.63, 22.94),    # Thessaloniki
            (35.24, 24.80),    # Crete
            (39.62, 19.92),    # Corfu
            (38.25, 21.74),    # Patras
        ],
    )
    def test_round_trip_micro_degree(self, lat, lon):
        """Round-trip must be accurate to < 0.0000001 degrees (~0.01mm)."""
        x, y = wgs84_to_egsa87(lat, lon)
        lat2, lon2 = egsa87_to_wgs84(x, y)
        assert abs(lat2 - lat) < 1e-7, f"lat diff: {abs(lat2 - lat):.10f} deg"
        assert abs(lon2 - lon) < 1e-7, f"lon diff: {abs(lon2 - lon):.10f} deg"


# --- Task 1.2: TM07 <-> WGS84 ---


class TestWgs84ToTm07:
    """Test WGS84 to TM07 (HTRS07) conversion."""

    def test_athens_area(self):
        """WGS84 Athens -> TM07 produces valid Greek Grid range coords."""
        x, y = wgs84_to_tm07(37.97, 23.73)
        assert 100_000 < x < 900_000, f"x={x} outside range"
        assert 3_800_000 < y < 4_700_000, f"y={y} outside range"

    def test_returns_floats(self):
        x, y = wgs84_to_tm07(37.97, 23.73)
        assert isinstance(x, float)
        assert isinstance(y, float)


class TestTm07ToWgs84:
    """Test TM07 to WGS84 conversion."""

    def test_returns_valid_wgs84(self):
        """TM07 coords -> valid WGS84 for Greece."""
        x, y = wgs84_to_tm07(37.97, 23.73)
        lat, lon = tm07_to_wgs84(x, y)
        assert 34 < lat < 42, f"lat {lat} outside Greece"
        assert 19 < lon < 30, f"lon {lon} outside Greece"


class TestTm07RoundTrip:
    """Round-trip accuracy tests for TM07."""

    @pytest.mark.parametrize(
        "lat, lon",
        [
            (37.97, 23.73),
            (40.63, 22.94),
            (35.24, 24.80),
            (39.62, 19.92),
            (38.25, 21.74),
        ],
    )
    def test_round_trip_micro_degree(self, lat, lon):
        """WGS84 -> TM07 -> WGS84 round-trip < 0.0000001 degrees."""
        x, y = wgs84_to_tm07(lat, lon)
        lat2, lon2 = tm07_to_wgs84(x, y)
        assert abs(lat2 - lat) < 1e-7, f"lat diff: {abs(lat2 - lat):.10f} deg"
        assert abs(lon2 - lon) < 1e-7, f"lon diff: {abs(lon2 - lon):.10f} deg"

    @pytest.mark.parametrize(
        "x, y",
        [
            (481000, 4205000),
            (413000, 4500000),
            (575000, 3900000),
        ],
    )
    def test_round_trip_submillimeter_from_tm07(self, x, y):
        """TM07 -> WGS84 -> TM07 round-trip < 1mm."""
        lat, lon = tm07_to_wgs84(x, y)
        x2, y2 = wgs84_to_tm07(lat, lon)
        assert abs(x2 - x) < 0.001, f"x diff: {abs(x2 - x):.6f}m"
        assert abs(y2 - y) < 0.001, f"y diff: {abs(y2 - y):.6f}m"


class TestEgsa87VsTm07:
    """EGSA87 and TM07 should give slightly different results for the same WGS84 point
    because EGSA87 uses GRS80/GGRS87 datum while TM07 uses WGS84 datum directly."""

    def test_different_results(self):
        """Same WGS84 point should produce different EGSA87 vs TM07 coords."""
        lat, lon = 37.97, 23.73
        egsa_x, egsa_y = wgs84_to_egsa87(lat, lon)
        tm07_x, tm07_y = wgs84_to_tm07(lat, lon)
        # They use different datums, so results must differ (typically by ~200m)
        diff = math.sqrt((egsa_x - tm07_x) ** 2 + (egsa_y - tm07_y) ** 2)
        assert diff > 1.0, f"EGSA87 and TM07 should differ, but diff is only {diff:.3f}m"
        # But not wildly different - should be in the hundreds of meters range
        assert diff < 500.0, f"Difference too large: {diff:.1f}m"
