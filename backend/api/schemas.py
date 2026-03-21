from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    business_type: str = Field(..., description="fast_food | dine_in | cafe | bubble_tea | retail")
    address: str
    max_staff: int = 5
    trading_hours: dict[str, Any] = Field(
        default_factory=lambda: {
            "hours": {str(d): [9, 21] for d in range(7)},
        }
    )
    signal_toggles: Optional[dict[str, bool]] = None


class LocationUpdate(BaseModel):
    business_type: Optional[str] = None
    address: Optional[str] = None
    max_staff: Optional[int] = None
    trading_hours: Optional[dict[str, Any]] = None
    signal_toggles: Optional[dict[str, bool]] = None
