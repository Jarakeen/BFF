from __future__ import annotations

"""Pydantic write boundary for Personnel and Team persistence."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from models.roster_model import ESO_CLASSES, STATUSES, normalize_roster_role


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


class PersonnelPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: int | None = Field(default=None, gt=0)
    player_name: str = Field(min_length=1, max_length=200)
    character_name: str = Field(default="", max_length=200)
    eso_class: str = Field(default="", max_length=80)
    primary_role: str = Field(default="", max_length=40)
    secondary_role: str = Field(default="", max_length=40)
    status: str = Field(default="Active", min_length=1, max_length=40)
    team: str = Field(default="", max_length=2000)
    canonical_player_id: str = Field(default="", max_length=240)
    canonical_character_id: str = Field(default="", max_length=240)
    discord_name: str = Field(default="", max_length=240)
    youtube: str = Field(default="", max_length=2000)
    twitch: str = Field(default="", max_length=2000)
    personnel_notes: str = Field(default="", max_length=12000)

    @field_validator("player_name", mode="before")
    @classmethod
    def required_player(cls, value: object) -> str:
        value = _clean(value)
        if not value:
            raise ValueError("player_name must not be blank")
        return value

    @field_validator("primary_role", "secondary_role", mode="before")
    @classmethod
    def canonical_role(cls, value: object) -> str:
        role = normalize_roster_role(value)
        if role not in {"", "Tank", "Healer", "DD"}:
            raise ValueError(f"unsupported Personnel role: {role!r}")
        return role

    @field_validator("eso_class")
    @classmethod
    def canonical_class(cls, value: str) -> str:
        if value and value not in set(ESO_CLASSES):
            raise ValueError(f"unsupported ESO class: {value!r}")
        return value

    @field_validator("status")
    @classmethod
    def canonical_status(cls, value: str) -> str:
        matches = {item.casefold(): item for item in STATUSES}
        canonical = matches.get(value.casefold())
        if canonical is None:
            raise ValueError(f"unsupported Personnel status: {value!r}")
        return canonical


class TeamScheduleSlotPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    day: str = Field(min_length=1, max_length=40)
    start_time: str = Field(min_length=1, max_length=40)
    end_time: str = Field(default="", max_length=40)


class TeamSchedulePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    team_name: str = Field(min_length=1, max_length=240)
    raid_days: str = Field(default="", max_length=500)
    raid_time: str = Field(default="", max_length=120)
    timezone: str = Field(default="", max_length=120)
    slots: tuple[TeamScheduleSlotPayload, ...] = ()
    current_focus: str = Field(default="", max_length=1000)
    discord_url: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def unique_days(self) -> "TeamSchedulePayload":
        days = [slot.day.casefold() for slot in self.slots]
        if len(days) != len(set(days)):
            raise ValueError("Team schedule cannot contain duplicate raid days")
        return self


def validate_personnel_payload(raw: Any) -> dict[str, Any]:
    return PersonnelPayload.model_validate(raw).model_dump(mode="python")


def validate_team_schedule_payload(raw: Any) -> dict[str, Any]:
    return TeamSchedulePayload.model_validate(raw).model_dump(mode="python")


__all__ = [
    "PersonnelPayload",
    "TeamSchedulePayload",
    "ValidationError",
    "validate_personnel_payload",
    "validate_team_schedule_payload",
]
