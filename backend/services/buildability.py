"""Deterministic buildability engine.

Computes what may be built on a parcel directly from the planning parameters
returned by the TEE Unified Digital Map — **no AI, no guessing**. Every output
is a pure function of the inputs so it is reproducible and defensible (an
engineer can stake their stamp on it).

The TEE layers return their values as human-readable Greek strings (e.g.
``"0,8"``, ``"60%"``, ``"11,00 μ."``), so the first job is robust parsing of
Greek-formatted numbers, then the planning arithmetic:

    max buildable floor area  = building_factor (Σ.Δ.) × parcel_area
    max ground footprint      = coverage_ratio (κάλυψη) × parcel_area
    indicative max floors     ≈ max_height / FLOOR_HEIGHT_M
    άρτιο (buildable lot)      = parcel_area ≥ min_lot_area (αρτιότητα)

All coefficients/labels are *inputs*; this module never invents a value. When a
parameter is missing it is reported as unknown rather than defaulted silently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Indicative storey height (m) used only to estimate floor count from a max
# height. Greek practice varies (ground floors are often taller); the result is
# explicitly flagged as indicative, never authoritative.
FLOOR_HEIGHT_M = 3.0


# ---------------------------------------------------------------------------
# Greek number parsing
# ---------------------------------------------------------------------------

def parse_greek_number(value) -> float | None:
    """Parse a Greek-formatted numeric string to a float.

    Handles comma decimal separators, dot/space thousands separators, a leading
    label, units, and a trailing percent sign. Returns ``None`` when no number
    can be extracted.

        "0,8"        -> 0.8
        "60%"        -> 60.0      (percent sign stripped; see as_ratio)
        "11,00 μ."   -> 11.0
        "1.200,50"   -> 1200.5
        "Σ.Δ. 2,4"   -> 2.4
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    if not s:
        return None

    # Grab the first number-like token (digits with , . and spaces between them)
    m = re.search(r"\d[\d.\s]*(?:,\d+)?|\d+(?:\.\d+)?", s)
    if not m:
        return None
    token = m.group(0).strip()

    if "," in token:
        # Greek style: '.' and spaces are thousands separators, ',' is decimal.
        token = token.replace(".", "").replace(" ", "").replace(",", ".")
    else:
        # No comma: spaces are thousands separators; a lone '.' is decimal.
        token = token.replace(" ", "")
    try:
        return float(token)
    except ValueError:
        return None


def as_ratio(value) -> float | None:
    """Parse a value that represents a ratio, normalizing percentages.

    ``"60%"`` -> 0.6, ``"0,6"`` -> 0.6, ``60`` -> 0.6, ``0.6`` -> 0.6.

    A bare number greater than 1 is treated as a percentage (coverage can never
    exceed 100%). Use this only for true ratios (coverage); do **not** use it for
    the building factor (Σ.Δ.), which is legitimately > 1.
    """
    n = parse_greek_number(value)
    if n is None:
        return None
    if "%" in str(value) or n > 1:
        return n / 100.0
    return n


# ---------------------------------------------------------------------------
# Inputs / outputs
# ---------------------------------------------------------------------------

@dataclass
class BuildabilityInput:
    """Structured planning parameters for one parcel. All optional — the engine
    reports what it can and flags what it cannot."""
    parcel_area_m2: float | None = None
    building_factor: float | None = None          # Σ.Δ. (ratio, may exceed 1)
    coverage_ratio: float | None = None           # κάλυψη (0–1)
    max_height_m: float | None = None             # μέγιστο ύψος
    min_lot_area_m2: float | None = None          # αρτιότητα (min οικόπεδο)
    min_frontage_m: float | None = None           # πρόσωπο
    plan_status: str | None = None                # within_plan / settlement / outside_plan


@dataclass
class BuildabilityResult:
    max_floor_area_m2: float | None = None        # max δόμηση
    max_footprint_m2: float | None = None         # max κάλυψη (ground)
    indicative_max_floors: int | None = None
    is_buildable_lot: bool | None = None          # άρτιο & οικοδομήσιμο
    inputs_used: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def compute_buildability(inp: BuildabilityInput) -> BuildabilityResult:
    """Deterministically compute buildability metrics from planning parameters."""
    r = BuildabilityResult()
    area = inp.parcel_area_m2

    if area is None or area <= 0:
        r.warnings.append("Εμβαδόν οικοπέδου άγνωστο — δεν υπολογίζεται δόμηση/κάλυψη.")
    else:
        r.inputs_used["parcel_area_m2"] = area

    # Max buildable floor area = Σ.Δ. × area
    if area and inp.building_factor is not None:
        r.max_floor_area_m2 = round(inp.building_factor * area, 2)
        r.inputs_used["building_factor"] = inp.building_factor
    elif inp.building_factor is None:
        r.warnings.append("Συντελεστής Δόμησης (Σ.Δ.) άγνωστος.")

    # Max ground footprint = coverage × area
    if area and inp.coverage_ratio is not None:
        r.max_footprint_m2 = round(inp.coverage_ratio * area, 2)
        r.inputs_used["coverage_ratio"] = inp.coverage_ratio
        if inp.coverage_ratio > 1:
            r.warnings.append("Συντελεστής κάλυψης > 100% — ελέγξτε τα δεδομένα.")
    elif inp.coverage_ratio is None:
        r.warnings.append("Συντελεστής κάλυψης άγνωστος.")

    # Indicative floor count from max height (estimate only)
    if inp.max_height_m is not None and inp.max_height_m > 0:
        r.indicative_max_floors = int(inp.max_height_m // FLOOR_HEIGHT_M)
        r.inputs_used["max_height_m"] = inp.max_height_m
        r.assumptions.append(
            f"Ενδεικτικός αριθμός ορόφων = μέγιστο ύψος / {FLOOR_HEIGHT_M:.1f}μ "
            "ανά όροφο (μη δεσμευτικό)."
        )

    # Buildable-lot check (αρτιότητα)
    if area and inp.min_lot_area_m2 is not None:
        r.is_buildable_lot = area >= inp.min_lot_area_m2
        r.inputs_used["min_lot_area_m2"] = inp.min_lot_area_m2
        if not r.is_buildable_lot:
            r.warnings.append(
                f"Το οικόπεδο ({area:.0f} m²) είναι μικρότερο της αρτιότητας "
                f"({inp.min_lot_area_m2:.0f} m²) — πιθανόν μη άρτιο/οικοδομήσιμο "
                "χωρίς παρεκκλίσεις."
            )

    if inp.plan_status == "outside_plan":
        r.assumptions.append(
            "Εκτός σχεδίου: ισχύουν ειδικοί όροι αρτιότητας/δόμησης — "
            "επιβεβαιώστε με την Πολεοδομία."
        )

    return r


# ---------------------------------------------------------------------------
# Bridge: TEE layer dict -> structured input
# ---------------------------------------------------------------------------

def _label_of(features: list) -> str | None:
    if features and isinstance(features, list):
        attrs = features[0].get("attributes", {})
        return attrs.get("LABEL") or attrs.get("label")
    return None


def extract_building_params(all_layers: dict, parcel_area_m2: float | None = None) -> BuildabilityInput:
    """Map the TEE ``get_all_layers`` output into a BuildabilityInput.

    Defensive: every field falls back to None when the layer is empty or the
    label cannot be parsed, so a partial dataset still yields a partial result.
    """
    plan_status = None
    if all_layers.get("city_plan_boundary"):
        plan_status = "within_plan"
    elif all_layers.get("settlement_boundary"):
        plan_status = "settlement"
    elif all_layers.get("outside_plan"):
        plan_status = "outside_plan"

    return BuildabilityInput(
        parcel_area_m2=parcel_area_m2,
        building_factor=parse_greek_number(_label_of(all_layers.get("sd", []))),
        coverage_ratio=as_ratio(_label_of(all_layers.get("coverage", []))),
        max_height_m=parse_greek_number(_label_of(all_layers.get("height", []))),
        min_lot_area_m2=parse_greek_number(_label_of(all_layers.get("artiotita", []))),
        plan_status=plan_status,
    )
