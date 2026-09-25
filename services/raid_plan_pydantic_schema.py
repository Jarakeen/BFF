from __future__ import annotations

"""Pydantic persistence boundary for Raid Plan payloads.

Domain ownership remains in the frozen dataclasses.  These schemas harden untrusted
JSON/backup/database payloads before they are allowed to construct domain snapshots.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


def _strip(value: object) -> str:
    return str(value or "").strip()


class _StrictPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RaidPlanCoverageProviderPayload(_StrictPayload):
    effect_name: str = Field(min_length=1, max_length=160)
    seat_id: str = Field(min_length=1, max_length=80)
    source: str = Field(min_length=1, max_length=500)
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("effect_name", "seat_id", "source", mode="before")
    @classmethod
    def required_text(cls, value: object) -> str:
        text = _strip(value)
        if not text:
            raise ValueError("must not be blank")
        return text

    @field_validator("effect_name")
    @classmethod
    def canonical_effect_name(cls, value: str) -> str:
        # Keep the human-facing catalog label stable while rejecting control
        # characters that can corrupt exports/logging.
        if any(ord(ch) < 32 and ch not in {"\t"} for ch in value):
            raise ValueError("effect_name contains control characters")
        return " ".join(value.split())

    @field_validator("source")
    @classmethod
    def safe_source(cls, value: str) -> str:
        if any(ord(ch) < 32 and ch not in {"\t"} for ch in value):
            raise ValueError("source contains control characters")
        return " ".join(value.split())

    @field_validator("note", mode="before")
    @classmethod
    def optional_text(cls, value: object) -> str | None:
        text = _strip(value)
        return text or None


class RaidPlanMemberPayload(_StrictPayload):
    seat_id: str = Field(min_length=1, max_length=80)
    gamertag: str = ""
    roster_member_id: int | None = Field(default=None, gt=0)
    player_id: str | None = None
    character_id: str | None = None
    character_name: str | None = None
    role: str | None = None
    eso_class: str | None = None
    selected_build_id: str | None = None
    selected_build_name: str | None = None
    build_source_kind: str | None = None
    build_source_name: str | None = None
    build_source_url: str | None = None
    candidate_id: str | None = None
    planned_gear_sets: tuple[str, ...] = ()
    planned_skills: tuple[str, ...] = ()
    planned_mundus: str | None = None
    primary_assignment: str | None = None
    secondary_assignment: str | None = None
    assignment_source: str | None = None
    utility_assignments: tuple[str, ...] = ()
    comp_locked_fields: tuple[str, ...] = ()
    notes: str | None = None

    @field_validator("seat_id", mode="before")
    @classmethod
    def seat_required(cls, value: object) -> str:
        text = _strip(value)
        if not text:
            raise ValueError("must not be blank")
        return text


class RaidPlanTriggeredResponsibilityPayload(_StrictPayload):
    responsibility_id: str = Field(min_length=1)
    seat_id: str = Field(min_length=1)
    encounter_id: str = Field(min_length=1)
    trigger_key: str = Field(min_length=1)
    directive: str = Field(min_length=1)
    target_key: str | None = None
    required_capability_type: str | None = None
    source: str | None = None


class RaidPlanPayload(_StrictPayload):
    plan_id: str = Field(min_length=1)
    trial_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    team_name: str | None = None
    difficulty: str | None = None
    status: Literal["planning", "active", "archived"] = "planning"
    members: tuple[RaidPlanMemberPayload, ...] = ()
    triggered_responsibilities: tuple[RaidPlanTriggeredResponsibilityPayload, ...] = ()
    coverage_providers: tuple[RaidPlanCoverageProviderPayload, ...] = ()
    plan_note: str | None = None

    @model_validator(mode="after")
    def validate_references(self) -> "RaidPlanPayload":
        seats = [row.seat_id.casefold() for row in self.members]
        if len(seats) != len(set(seats)):
            raise ValueError("member seat_id values must be unique")
        known = set(seats)
        for row in self.triggered_responsibilities:
            if row.seat_id.casefold() not in known:
                raise ValueError(f"triggered responsibility references unknown seat_id: {row.seat_id!r}")
        coverage_keys: set[tuple[str, str]] = set()
        for row in self.coverage_providers:
            if row.seat_id.casefold() not in known:
                raise ValueError(f"coverage provider references unknown seat_id: {row.seat_id!r}")
            key = (row.effect_name.casefold(), row.seat_id.casefold())
            if key in coverage_keys:
                raise ValueError(
                    "duplicate coverage provider for effect/seat: "
                    f"{row.effect_name!r} / {row.seat_id!r}"
                )
            coverage_keys.add(key)
        return self


def validate_raid_plan_payload(raw: Any) -> dict[str, Any]:
    """Validate and normalize one persisted plan, returning plain Python values."""
    return RaidPlanPayload.model_validate(raw).model_dump(mode="python")


__all__ = [
    "RaidPlanCoverageProviderPayload",
    "RaidPlanPayload",
    "ValidationError",
    "validate_raid_plan_payload",
]
