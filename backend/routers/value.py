"""Objective property value (αντικειμενική αξία) endpoint."""

from dataclasses import asdict

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.objective_value import (
    ObjectiveValueInput,
    compute_objective_value,
)

router = APIRouter(prefix="/api/v1/value", tags=["value"])


class ObjectiveValueRequest(BaseModel):
    zone_price: float | None = None            # Τ.Ζ. €/m² (from valuemaps.gsis.gr)
    area_m2: float | None = None
    year_built: int | None = None
    ref_year: int | None = None
    has_frontage: bool | None = None
    floor_coefficient: float = 1.0             # Σ.Ο.
    surface_coefficient: float = 1.0           # Σ.Επιφανείας
    commerciality_coefficient: float = 1.0     # Σ.Εμπορικότητας
    coownership_share: float = 1.0
    special_conditions_coefficient: float = 1.0


class ObjectiveValueResponse(BaseModel):
    objective_value: float | None = None
    coefficients: dict = {}
    warnings: list[str] = []
    assumptions: list[str] = []


@router.post("/objective", response_model=ObjectiveValueResponse)
async def objective_value(req: ObjectiveValueRequest):
    """Compute the within-plan dwelling objective value deterministically.

    Every coefficient used is returned so the figure is auditable. The zone
    price (Τ.Ζ.) is supplied by the caller — sourced from valuemaps.gsis.gr.
    """
    result = compute_objective_value(
        ObjectiveValueInput(
            zone_price=req.zone_price,
            area_m2=req.area_m2,
            year_built=req.year_built,
            ref_year=req.ref_year,
            has_frontage=req.has_frontage,
            floor_coefficient=req.floor_coefficient,
            surface_coefficient=req.surface_coefficient,
            commerciality_coefficient=req.commerciality_coefficient,
            coownership_share=req.coownership_share,
            special_conditions_coefficient=req.special_conditions_coefficient,
        )
    )
    return ObjectiveValueResponse(**asdict(result))
