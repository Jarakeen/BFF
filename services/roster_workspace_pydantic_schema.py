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


class RecruitmentCandidatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: int | None = Field(default=None, gt=0)
    player_name: str = Field(default="", max_length=500)
    character_name: str = Field(default="", max_length=500)
    desired_role: str = Field(default="", max_length=120)
    eso_class: str = Field(default="", max_length=120)
    target_team: str = Field(default="", max_length=500)
    availability: str = Field(default="", max_length=2000)
    status: str = Field(max_length=40)
    notes: str = Field(default="", max_length=8000)


class RosterArchivePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    entity_type: str = Field(min_length=1, max_length=120)
    entity_key: str = Field(default="", max_length=500)
    display_name: str = Field(min_length=1, max_length=500)
    reason: str = Field(default="", max_length=2000)
    related_team: str = Field(default="", max_length=500)
    payload: dict[str, Any] = Field(default_factory=dict)


def validate_recruitment_candidate(raw: Any) -> dict[str, Any]:
    return RecruitmentCandidatePayload.model_validate(raw).model_dump(mode="python")


def validate_roster_archive(raw: Any) -> dict[str, Any]:
    return RosterArchivePayload.model_validate(raw).model_dump(mode="python")
