"""Objective property value (αντικειμενική αξία) calculator.

Implements the Greek objective-value system for a **building/dwelling within
plan or settlement** (κατοικία/διαμέρισμα εντός σχεδίου ή οικισμού) per the
codified methodology of ΠΟΛ.1149/1994. The taxable value is a product of the
zone price and a set of coefficients:

    Φ.Α. = Τ.Ζ. × Επιφάνεια × Σ.Ο. × Σ.Π. × Σ.Πρόσοψης × Σ.Επιφανείας
           × Σ.Ειδικών_Συνθηκών × ποσοστό_συνιδιοκτησίας

This module is **deterministic and fully transparent**: every coefficient used
is reported in the result so the figure is auditable. Like the buildability
engine, it never silently defaults — coefficients we cannot derive without the
official lookup tables are accepted as inputs (default 1.0) and flagged.

Authoritative values encoded here:
  * Age coefficient (Σ.Π.) — bracket table (≤5y→0.90 … ≥26y→0.60).
  * Frontage coefficient (Σ.Πρόσοψης) — 1.00 with frontage / 0.80 without.

NOT encoded (must come from the official ΑΠΑΑ tables, passed in as inputs):
  * Floor coefficient (Σ.Ο.) — a 2-D matrix of floor × commerciality (0.60–1.30).
  * Surface coefficient (Σ.Επιφανείας), special-conditions, commerciality.

Out of scope (different formulas): land-only parcels (οικόπεδα) and out-of-plan
properties (εκτός σχεδίου, ΠΟΛ.1310/1996), which use Σ.Ο./Σ.Α.Ο. coefficients.

The zone price (Τ.Ζ.) is sourced from ΑΑΔΕ price zones (valuemaps.gsis.gr); here
it is an explicit input. All published coefficient tables should be verified
against the ΑΠΑΑ decision in force for the transaction date before relying on a
figure for an official deliverable.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

# Age coefficient (Συντελεστής Παλαιότητας) — current bracketed table.
# (lower_bound_years_inclusive, coefficient); below the first bound => 1.00 (new).
# Source: codified ΑΠΑΑ / ΠΟΛ.1149/1994 age table (current 6-bracket form).
_AGE_TABLE = [
    (26, 0.60),
    (21, 0.65),
    (16, 0.70),
    (11, 0.75),
    (6, 0.80),
    (1, 0.90),
]
_AGE_NEW = 1.00

# Frontage coefficient (Συντελεστής Πρόσοψης).
_FRONTAGE_WITH = 1.00
_FRONTAGE_WITHOUT = 0.80


def age_coefficient(years: float | None) -> float | None:
    """Return Σ.Π. for a building of the given age in years.

    <1 year (new/under construction) → 1.00; then 0.90 (1–5y) down to 0.60 (≥26y).
    """
    if years is None:
        return None
    if years < 1:
        return _AGE_NEW
    for lower, coef in _AGE_TABLE:
        if years >= lower:
            return coef
    return _AGE_NEW


def frontage_coefficient(has_frontage: bool | None) -> float | None:
    if has_frontage is None:
        return None
    return _FRONTAGE_WITH if has_frontage else _FRONTAGE_WITHOUT


@dataclass
class ObjectiveValueInput:
    """Inputs for a within-plan dwelling objective value.

    ``zone_price`` (Τ.Ζ., €/m²) and ``area_m2`` are required for a figure.
    ``year_built`` + ``ref_year`` drive the age coefficient; ``has_frontage``
    drives the frontage coefficient. The remaining coefficients come from the
    official ΑΠΑΑ tables and default to 1.0 (neutral) when not supplied.
    """
    zone_price: float | None = None            # Τ.Ζ. €/m²
    area_m2: float | None = None
    year_built: int | None = None
    ref_year: int | None = None                # defaults to current year
    has_frontage: bool | None = None
    floor_coefficient: float = 1.0             # Σ.Ο. — from official matrix
    surface_coefficient: float = 1.0           # Σ.Επιφανείας
    commerciality_coefficient: float = 1.0     # Σ.Εμπορικότητας (commercial)
    coownership_share: float = 1.0             # ποσοστό συνιδιοκτησίας
    special_conditions_coefficient: float = 1.0  # Σ.Ειδικών Συνθηκών


@dataclass
class ObjectiveValueResult:
    objective_value: float | None = None
    coefficients: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


def compute_objective_value(inp: ObjectiveValueInput) -> ObjectiveValueResult:
    """Deterministically compute the within-plan dwelling objective value."""
    r = ObjectiveValueResult()

    if inp.zone_price is None or inp.zone_price <= 0:
        r.warnings.append("Τιμή Ζώνης (Τ.Ζ.) άγνωστη — δεν υπολογίζεται αξία. "
                          "Αντλείται από valuemaps.gsis.gr.")
    if inp.area_m2 is None or inp.area_m2 <= 0:
        r.warnings.append("Επιφάνεια άγνωστη — δεν υπολογίζεται αξία.")

    # Age coefficient
    sp = None
    if inp.year_built is not None:
        ref = inp.ref_year or datetime.date.today().year
        age = ref - inp.year_built
        sp = age_coefficient(age)
        r.assumptions.append(
            f"Συντελεστής Παλαιότητας {sp} (ηλικία {age} έτη, έτος αναφοράς {ref})."
        )
    else:
        sp = 1.0
        r.warnings.append("Έτος κατασκευής άγνωστο — Σ.Π. = 1,00 (νεόδμητο). "
                          "Δηλώστε έτος για ακριβή υπολογισμό.")

    # Frontage coefficient
    spros = frontage_coefficient(inp.has_frontage)
    if spros is None:
        spros = 1.0
        r.warnings.append("Πρόσοψη άγνωστη — Σ.Πρόσοψης = 1,00.")

    # Flag any neutral defaults that should come from the official tables.
    for name, val, note in (
        ("Σ.Ο. (ορόφου)", inp.floor_coefficient, "από επίσημο πίνακα ΑΠΑΑ"),
        ("Σ.Επιφανείας", inp.surface_coefficient, "από επίσημο πίνακα"),
        ("Σ.Εμπορικότητας", inp.commerciality_coefficient, "για εμπορικά ακίνητα"),
    ):
        if val == 1.0:
            r.assumptions.append(f"{name} = 1,00 (προεπιλογή — επιβεβαιώστε {note}).")

    coefs = {
        "zone_price": inp.zone_price,
        "area_m2": inp.area_m2,
        "age": sp,
        "frontage": spros,
        "floor": inp.floor_coefficient,
        "surface": inp.surface_coefficient,
        "commerciality": inp.commerciality_coefficient,
        "coownership": inp.coownership_share,
        "special_conditions": inp.special_conditions_coefficient,
    }
    r.coefficients = coefs

    if inp.zone_price and inp.area_m2:
        value = (
            inp.zone_price
            * inp.area_m2
            * sp
            * spros
            * inp.floor_coefficient
            * inp.surface_coefficient
            * inp.commerciality_coefficient
            * inp.coownership_share
            * inp.special_conditions_coefficient
        )
        r.objective_value = round(value, 2)

    return r
