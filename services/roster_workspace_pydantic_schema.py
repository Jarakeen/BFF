from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CanonicalPersonnelBindingPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    roster_member_id: int = Field(gt=0)
    canonical_player_id: str = Field(default="", max_length=240)
    canonical_character_id: str = Field(default="", max_length=240)


class RosterAvailabilityPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    roster_member_id: int = Field(gt=0)
    monday: str = Field(max_length=20)
    tuesday: str = Field(max_length=20)
    wednesday: str = Field(max_length=20)
    thursday: str = Field(max_length=20)
    friday: str = Field(max_length=20)
    saturday: str = Field(max_length=20)
    sunday: str = Field(max_length=20)
    preferred_times: str = Field(default="", max_length=1000)
    notes: str = Field(default="", max_length=8000)


def validate_canonical_personnel_binding(raw: Any) -> dict[str, Any]:
    return CanonicalPersonnelBindingPayload.model_validate(raw).model_dump(mode="python")


def validate_roster_availability(raw: Any) -> dict[str, Any]:
    return RosterAvailabilityPayload.model_validate(raw).model_dump(mode="python")
