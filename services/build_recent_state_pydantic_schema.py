from __future__ import annotations

"""Strict Pydantic boundary for recently added Saved Build identity/mastery state."""

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator


class BuildRecentStatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    eso_class: str
    vampire: bool = False
    werewolf: bool = False
    class_skill_lines: tuple[str, ...] = ()
    class_mastery_ability_ids: tuple[int, ...] = ()

    @field_validator("eso_class")
    @classmethod
    def normalize_class(cls, value: str) -> str:
        value = value.strip()
        if len(value) > 80:
            raise ValueError("ESO class is too long")
        return value

    @field_validator("class_skill_lines")
    @classmethod
    def validate_skill_lines(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(value.strip() for value in values)
        if any(not value or len(value) > 120 for value in cleaned):
            raise ValueError("class skill-line identities must be nonblank and bounded")
        if len({value.casefold() for value in cleaned}) != len(cleaned):
            raise ValueError("class skill-line identities must be unique")
        return cleaned

    @field_validator("class_mastery_ability_ids")
    @classmethod
    def validate_masteries(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        if len(values) > 2:
            raise ValueError("a Saved Build may select at most two Class Masteries")
        if any(value <= 0 for value in values):
            raise ValueError("Class Mastery ability ids must be positive")
        if len(set(values)) != len(values):
            raise ValueError("Class Mastery ability ids must be unique")
        return values

    @model_validator(mode="after")
    def validate_world_state(self):
        if self.vampire and self.werewolf:
            raise ValueError("a Saved Build cannot be both Vampire and Werewolf")
        if self.class_skill_lines and self.class_mastery_ability_ids:
            raise ValueError("subclassed Builds cannot select Class Masteries")
        return self


def validate_build_recent_state_payload(raw: dict[str, Any]) -> dict[str, Any]:
    model = BuildRecentStatePayload.model_validate(raw)
    return model.model_dump(mode="python")


__all__ = ["BuildRecentStatePayload", "ValidationError", "validate_build_recent_state_payload"]
