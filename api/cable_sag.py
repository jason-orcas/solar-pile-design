"""FastAPI endpoint for Cable Sag & Clearance Analysis.

Can be run standalone:
    uvicorn api.cable_sag:app --port 8100

Or imported into another FastAPI app:
    from api.cable_sag import router
    app.include_router(router, prefix="/cable-sag")
"""

import sys
from pathlib import Path

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add project root so we can import core/
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cable_sag import (
    cable_clearance_check,
    cab_loaded_sag,
    cab_bare_sag,
    cab_pier_reactions,
    awm_sag,
    CableSagResult,
)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class CableSagRequest(BaseModel):
    """Request body for cable sag & clearance analysis."""

    system: str = Field(
        ..., description="Cable management system: 'CAB' or 'AWM'",
        pattern="^(CAB|AWM)$",
    )
    span_ft: float = Field(..., gt=0, description="Span between piles (ft)")
    wire_weight_plf: float = Field(
        ..., gt=0, description="Wire weight including cables (lb/ft)"
    )
    actual_reveal_ft: float = Field(
        ..., gt=0, description="Actual pile height above grade (ft)"
    )

    # Clearance geometry
    ground_clearance_in: float = Field(
        18.0, ge=0, description="Required ground clearance (in)"
    )
    flood_freeboard_in: float = Field(
        0.0, ge=0, description="Flood freeboard (in), 0 if N/A"
    )
    bracket_drop_in: float = Field(
        5.5, description="Bracket offset below mounting point (in). "
        "CAB ~5.5 (L-bracket); AWM ~ -1 (raises wire)"
    )
    hanger_height_in: float = Field(
        8.0, ge=0, description="Messenger to bottom of lowest cable (in)"
    )
    pile_top_clearance_in: float = Field(
        1.0, ge=0, description="Clearance from pile top to bracket (in)"
    )

    # Temperature
    temp_min_f: float = Field(0.0, description="Site min temperature (deg F)")
    temp_max_f: float = Field(120.0, description="Site max temperature (deg F)")

    # CAB-specific
    wind_speed_mph: float = Field(
        115.0, ge=0, description="Design wind speed (mph), for CAB pier reactions"
    )

    # AWM-specific
    awm_tension_lbs: float | None = Field(
        None, ge=0, description="AWM stringing tension (lbs)"
    )
    awm_allowable_sag_in: float | None = Field(
        None, ge=0, description="AWM allowable sag (in) — alternative to tension"
    )
    temp_sag_in: float | None = Field(
        None, ge=0, description="Manual temperature sag (in). None = auto"
    )


class CableSagResponse(BaseModel):
    """Response body with full analysis results."""

    system: str
    span_ft: float
    wire_weight_plf: float

    # Sag
    sag_in: float
    sag_ft: float

    # Clearance
    mounting_height_in: float
    bracket_drop_in: float
    hanger_height_in: float
    pile_top_clearance_in: float
    ground_clearance_req_in: float
    flood_freeboard_in: float
    min_reveal_in: float
    min_reveal_ft: float
    actual_reveal_in: float
    actual_reveal_ft: float
    clearance_at_midspan_in: float
    passes: bool

    # Pier loads
    V_vertical_lbs: float
    H_longitudinal_lbs: float
    H_transverse_lbs: float

    # Temperature
    temp_min_f: float
    temp_max_f: float

    notes: list[str]


class QuickSagRequest(BaseModel):
    """Lightweight request for sag-only calculation (no clearance check)."""

    system: str = Field(..., pattern="^(CAB|AWM)$")
    span_ft: float = Field(..., gt=0)
    wire_weight_plf: float = Field(..., gt=0)
    temp_f: float = Field(60.0, description="Temperature (deg F)")
    awm_tension_lbs: float | None = Field(None, ge=0)


class QuickSagResponse(BaseModel):
    """Sag-only result."""

    system: str
    sag_in: float
    sag_ft: float
    tension_lbs: float | None = None


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["Cable Sag"])


@router.post("/analyze", response_model=CableSagResponse)
def analyze_cable_sag(req: CableSagRequest):
    """Run full cable sag analysis with clearance check and pier loads."""
    result = cable_clearance_check(
        system=req.system,
        span_ft=req.span_ft,
        wire_weight_plf=req.wire_weight_plf,
        actual_reveal_ft=req.actual_reveal_ft,
        ground_clearance_in=req.ground_clearance_in,
        flood_freeboard_in=req.flood_freeboard_in,
        bracket_drop_in=req.bracket_drop_in,
        hanger_height_in=req.hanger_height_in,
        pile_top_clearance_in=req.pile_top_clearance_in,
        temp_min_f=req.temp_min_f,
        temp_max_f=req.temp_max_f,
        wind_speed_mph=req.wind_speed_mph,
        awm_tension_lbs=req.awm_tension_lbs,
        awm_allowable_sag_in=req.awm_allowable_sag_in,
        temp_sag_in=req.temp_sag_in,
    )

    return CableSagResponse(
        system=result.system,
        span_ft=result.span_ft,
        wire_weight_plf=result.wire_weight_plf,
        sag_in=result.sag_in,
        sag_ft=result.sag_ft,
        mounting_height_in=result.mounting_height_in,
        bracket_drop_in=result.bracket_drop_in,
        hanger_height_in=result.hanger_height_in,
        pile_top_clearance_in=result.pile_top_clearance_in,
        ground_clearance_req_in=result.ground_clearance_req_in,
        flood_freeboard_in=result.flood_freeboard_in,
        min_reveal_in=result.min_reveal_in,
        min_reveal_ft=result.min_reveal_ft,
        actual_reveal_in=result.actual_reveal_in,
        actual_reveal_ft=result.actual_reveal_ft,
        clearance_at_midspan_in=result.clearance_at_midspan_in,
        passes=result.passes,
        V_vertical_lbs=result.V_vertical_lbs,
        H_longitudinal_lbs=result.H_longitudinal_lbs,
        H_transverse_lbs=result.H_transverse_lbs,
        temp_min_f=result.temp_min_f,
        temp_max_f=result.temp_max_f,
        notes=result.notes,
    )


@router.post("/sag", response_model=QuickSagResponse)
def quick_sag(req: QuickSagRequest):
    """Quick sag-only calculation (no clearance check or pier loads)."""
    if req.system == "CAB":
        sag_in = cab_loaded_sag(req.span_ft, req.wire_weight_plf, req.temp_f)
        return QuickSagResponse(
            system="CAB", sag_in=sag_in, sag_ft=sag_in / 12.0,
        )
    else:
        sag_in, tension = awm_sag(
            req.span_ft, req.wire_weight_plf,
            tension_lbs=req.awm_tension_lbs,
        )
        return QuickSagResponse(
            system="AWM", sag_in=sag_in, sag_ft=sag_in / 12.0,
            tension_lbs=tension,
        )


# ---------------------------------------------------------------------------
# Standalone app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SPORK Cable Sag API",
    description="Cable sag & clearance analysis for solar wire management (CAB / AWM).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/cable-sag")


@app.get("/health")
def health():
    return {"status": "ok"}
