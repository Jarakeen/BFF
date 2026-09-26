from __future__ import annotations

"""Strict validation for user-owned achievement progress snapshots."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AchievementProgressSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    active_profile: str = Field(min_length=1, max_length=240)
    profiles: dict[str, tuple[str, ...]] = Field(min_length=1)

    @field_validator("profiles")
    @classmethod
    def validate_profiles(cls, value: dict[str, tuple[str, ...]]) -> dict[str, tuple[str, ...]]:
        for name, ids in value.items():
            if not name.strip() or len(name) > 240:
                raise ValueError("Achievement profile names must be 1-240 characters")
            if any(not item.strip() or len(item) > 240 for item in ids):
                raise ValueError(f"Achievement profile {name!r} contains an invalid achievement id")
            folded = [item.casefold() for item in ids]
            if len(folded) != len(set(folded)):
                raise ValueError(f"Achievement profile {name!r} contains duplicate achievement ids")
        return value

    @model_validator(mode="after")
    def active_profile_exists(self) -> "AchievementProgressSnapshot":
        if self.active_profile not in self.profiles:
            raise ValueError("Active achievement profile must exist in profiles")
        return self


def validate_achievement_progress_snapshot(raw: Any) -> dict[str, Any]:
    return AchievementProgressSnapshot.model_validate(raw).model_dump(mode="json")
