"""Tests for static JSON data files."""

import json
import os
import pytest

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "data")


class TestZoningRules:
    @pytest.fixture(autouse=True)
    def load_data(self):
        with open(os.path.join(DATA_DIR, "zoning_rules.json")) as f:
            self.data = json.load(f)

    def test_valid_json_and_is_list(self):
        assert isinstance(self.data, list)

    def test_eight_zones(self):
        assert len(self.data) == 8

    REQUIRED_KEYS = [
        "name", "coverage_ratio", "building_factor", "max_height_m",
        "min_lot_size_m2", "max_floors", "setback_front_m", "setback_side_m",
    ]

    def test_each_zone_has_required_keys(self):
        for zone in self.data:
            for key in self.REQUIRED_KEYS:
                assert key in zone, f"Zone '{zone.get('name', '?')}' missing key '{key}'"

    def test_coverage_ratio_range(self):
        for zone in self.data:
            assert 0 < zone["coverage_ratio"] <= 1, f"{zone['name']}: coverage={zone['coverage_ratio']}"

    def test_height_positive(self):
        for zone in self.data:
            assert zone["max_height_m"] > 0, f"{zone['name']}: height={zone['max_height_m']}"

    def test_building_factor_positive(self):
        for zone in self.data:
            assert zone["building_factor"] > 0, f"{zone['name']}: factor={zone['building_factor']}"

    def test_min_lot_size_positive(self):
        for zone in self.data:
            assert zone["min_lot_size_m2"] > 0

    def test_max_floors_positive_int(self):
        for zone in self.data:
            assert isinstance(zone["max_floors"], int)
            assert zone["max_floors"] > 0

    def test_each_zone_has_fek(self):
        for zone in self.data:
            assert "fek" in zone, f"Zone '{zone['name']}' missing 'fek'"
            assert zone["fek"], f"Zone '{zone['name']}' has empty fek"

    def test_zone_names_unique(self):
        names = [z["name"] for z in self.data]
        assert len(names) == len(set(names))


class TestNatura2000:
    @pytest.fixture(autouse=True)
    def load_data(self):
        with open(os.path.join(DATA_DIR, "natura2000_areas.json")) as f:
            self.data = json.load(f)

    def test_valid_json_and_is_list(self):
        assert isinstance(self.data, list)

    def test_approximately_eight_entries(self):
        assert 6 <= len(self.data) <= 12

    REQUIRED_KEYS = ["code", "name", "center_lat", "center_lon", "protection_level", "type", "area_ha"]

    def test_each_entry_has_required_keys(self):
        for entry in self.data:
            for key in self.REQUIRED_KEYS:
                assert key in entry, f"'{entry.get('name', '?')}' missing '{key}'"

    def test_coordinates_within_greece(self):
        for entry in self.data:
            assert 34 <= entry["center_lat"] <= 42, f"{entry['name']}: lat={entry['center_lat']}"
            assert 19 <= entry["center_lon"] <= 30, f"{entry['name']}: lon={entry['center_lon']}"

    def test_area_positive(self):
        for entry in self.data:
            assert entry["area_ha"] > 0


class TestArchaeologicalZones:
    @pytest.fixture(autouse=True)
    def load_data(self):
        with open(os.path.join(DATA_DIR, "archaeological_zones.json")) as f:
            self.data = json.load(f)

    def test_valid_json_and_is_list(self):
        assert isinstance(self.data, list)

    def test_approximately_ten_entries(self):
        assert 8 <= len(self.data) <= 14

    REQUIRED_KEYS = ["name", "center_lat", "center_lon", "protection_level", "type"]

    def test_each_entry_has_required_keys(self):
        for entry in self.data:
            for key in self.REQUIRED_KEYS:
                assert key in entry, f"'{entry.get('name', '?')}' missing '{key}'"

    def test_coordinates_within_greece(self):
        for entry in self.data:
            assert 34 <= entry["center_lat"] <= 42, f"{entry['name']}: lat={entry['center_lat']}"
            assert 19 <= entry["center_lon"] <= 30, f"{entry['name']}: lon={entry['center_lon']}"
