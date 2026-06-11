"""Tests for the objective-value (αντικειμενική αξία) calculator."""

from backend.services.objective_value import (
    age_coefficient,
    frontage_coefficient,
    compute_objective_value,
    ObjectiveValueInput,
)


class TestAgeCoefficient:
    def test_new_building(self):
        assert age_coefficient(0) == 1.00
        assert age_coefficient(0.5) == 1.00

    def test_brackets(self):
        assert age_coefficient(3) == 0.90      # 1–5
        assert age_coefficient(5) == 0.90
        assert age_coefficient(8) == 0.80      # 6–10
        assert age_coefficient(13) == 0.75     # 11–15
        assert age_coefficient(18) == 0.70     # 16–20
        assert age_coefficient(23) == 0.65     # 21–25
        assert age_coefficient(26) == 0.60     # ≥26
        assert age_coefficient(80) == 0.60

    def test_none(self):
        assert age_coefficient(None) is None


class TestFrontageCoefficient:
    def test_values(self):
        assert frontage_coefficient(True) == 1.00
        assert frontage_coefficient(False) == 0.80
        assert frontage_coefficient(None) is None


class TestComputeObjectiveValue:
    def test_basic_known_figure(self):
        # 1500 €/m² × 100 m² × age(10y)=0.80 × frontage=1.0 = 120,000
        inp = ObjectiveValueInput(
            zone_price=1500.0, area_m2=100.0,
            year_built=2016, ref_year=2026, has_frontage=True,
        )
        r = compute_objective_value(inp)
        assert r.objective_value == 120000.0
        assert r.coefficients["age"] == 0.80
        assert r.coefficients["frontage"] == 1.00

    def test_no_frontage_discount(self):
        inp = ObjectiveValueInput(
            zone_price=1000.0, area_m2=50.0,
            year_built=2026, ref_year=2026, has_frontage=False,
        )
        r = compute_objective_value(inp)
        # 1000 × 50 × age(new)=1.0 × frontage=0.8 = 40,000
        assert r.objective_value == 40000.0

    def test_coownership_and_floor(self):
        inp = ObjectiveValueInput(
            zone_price=2000.0, area_m2=80.0,
            year_built=2026, ref_year=2026, has_frontage=True,
            floor_coefficient=1.10, coownership_share=0.5,
        )
        r = compute_objective_value(inp)
        # 2000 × 80 × 1.0 × 1.0 × 1.10 × 0.5 = 88,000
        assert r.objective_value == 88000.0

    def test_missing_zone_price_warns_no_value(self):
        r = compute_objective_value(ObjectiveValueInput(area_m2=100.0))
        assert r.objective_value is None
        assert any("Τιμή Ζώνης" in w for w in r.warnings)

    def test_missing_year_assumes_new_and_warns(self):
        r = compute_objective_value(
            ObjectiveValueInput(zone_price=1000.0, area_m2=10.0, has_frontage=True)
        )
        assert r.coefficients["age"] == 1.0
        assert any("Έτος κατασκευής" in w for w in r.warnings)
        assert r.objective_value == 10000.0

    def test_default_coefficients_are_flagged(self):
        r = compute_objective_value(
            ObjectiveValueInput(zone_price=1000.0, area_m2=10.0,
                                year_built=2026, ref_year=2026, has_frontage=True)
        )
        assert any("Σ.Ο." in a for a in r.assumptions)

    def test_deterministic(self):
        inp = ObjectiveValueInput(zone_price=1234.0, area_m2=77.0,
                                  year_built=2000, ref_year=2026, has_frontage=True)
        assert compute_objective_value(inp).objective_value == \
            compute_objective_value(inp).objective_value
