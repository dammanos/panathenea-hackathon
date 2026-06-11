"""Tests for the deterministic buildability engine."""

from backend.services.buildability import (
    parse_greek_number,
    as_ratio,
    compute_buildability,
    extract_building_params,
    BuildabilityInput,
    FLOOR_HEIGHT_M,
)


class TestParseGreekNumber:
    def test_comma_decimal(self):
        assert parse_greek_number("0,8") == 0.8

    def test_with_unit(self):
        assert parse_greek_number("11,00 μ.") == 11.0

    def test_thousands_separator(self):
        assert parse_greek_number("1.200,50") == 1200.5

    def test_leading_label(self):
        assert parse_greek_number("Σ.Δ. 2,4") == 2.4

    def test_percent_token_kept_as_number(self):
        assert parse_greek_number("60%") == 60.0

    def test_plain_float_and_int(self):
        assert parse_greek_number(0.6) == 0.6
        assert parse_greek_number(300) == 300.0

    def test_unparseable_returns_none(self):
        assert parse_greek_number("") is None
        assert parse_greek_number(None) is None
        assert parse_greek_number("άγνωστο") is None


class TestAsRatio:
    def test_percent_string(self):
        assert as_ratio("60%") == 0.6

    def test_decimal_string(self):
        assert as_ratio("0,6") == 0.6

    def test_bare_number_over_one_is_percent(self):
        assert as_ratio(60) == 0.6

    def test_bare_fraction_kept(self):
        assert as_ratio(0.6) == 0.6

    def test_none(self):
        assert as_ratio(None) is None


class TestComputeBuildability:
    def test_normal_within_plan_parcel(self):
        inp = BuildabilityInput(
            parcel_area_m2=1000.0,
            building_factor=0.8,
            coverage_ratio=0.6,
            max_height_m=11.0,
            min_lot_area_m2=300.0,
            plan_status="within_plan",
        )
        r = compute_buildability(inp)
        assert r.max_floor_area_m2 == 800.0
        assert r.max_footprint_m2 == 600.0
        assert r.indicative_max_floors == int(11.0 // FLOOR_HEIGHT_M)  # 3
        assert r.is_buildable_lot is True
        assert r.warnings == []

    def test_sub_artiotita_parcel_warns(self):
        inp = BuildabilityInput(
            parcel_area_m2=200.0,
            building_factor=0.8,
            min_lot_area_m2=300.0,
        )
        r = compute_buildability(inp)
        assert r.is_buildable_lot is False
        assert any("αρτιότητας" in w for w in r.warnings)

    def test_missing_area_skips_area_dependent_metrics(self):
        r = compute_buildability(BuildabilityInput(building_factor=0.8))
        assert r.max_floor_area_m2 is None
        assert any("Εμβαδόν" in w for w in r.warnings)

    def test_missing_factor_warns(self):
        r = compute_buildability(BuildabilityInput(parcel_area_m2=500.0))
        assert r.max_floor_area_m2 is None
        assert any("Σ.Δ." in w for w in r.warnings)

    def test_outside_plan_adds_assumption(self):
        r = compute_buildability(
            BuildabilityInput(parcel_area_m2=4000.0, building_factor=0.2,
                              plan_status="outside_plan")
        )
        assert any("Εκτός σχεδίου" in a for a in r.assumptions)

    def test_deterministic(self):
        inp = BuildabilityInput(parcel_area_m2=1234.0, building_factor=1.2,
                                coverage_ratio=0.5)
        assert compute_buildability(inp).max_floor_area_m2 == \
            compute_buildability(inp).max_floor_area_m2 == round(1.2 * 1234.0, 2)


class TestExtractBuildingParams:
    def _layer(self, label):
        return [{"attributes": {"LABEL": label}}]

    def test_maps_labels_and_plan_status(self):
        all_layers = {
            "sd": self._layer("0,8"),
            "coverage": self._layer("60%"),
            "height": self._layer("11,00 μ."),
            "artiotita": self._layer("300"),
            "city_plan_boundary": [{"attributes": {}}],
        }
        inp = extract_building_params(all_layers, parcel_area_m2=1000.0)
        assert inp.building_factor == 0.8
        assert inp.coverage_ratio == 0.6
        assert inp.max_height_m == 11.0
        assert inp.min_lot_area_m2 == 300.0
        assert inp.plan_status == "within_plan"

    def test_empty_layers_yield_none(self):
        inp = extract_building_params({}, parcel_area_m2=None)
        assert inp.building_factor is None
        assert inp.plan_status is None

    def test_end_to_end_partial_data(self):
        all_layers = {"sd": self._layer("1,2"), "outside_plan": [{"attributes": {}}]}
        inp = extract_building_params(all_layers, parcel_area_m2=2000.0)
        r = compute_buildability(inp)
        assert r.max_floor_area_m2 == 2400.0
        assert r.max_footprint_m2 is None  # no coverage layer
        assert inp.plan_status == "outside_plan"
