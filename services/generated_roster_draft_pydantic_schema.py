from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GeneratedRosterDraftSlotPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    slot_name: str = Field(min_length=1, max_length=120)
    kind: str = Field(min_length=1, max_length=120)
    player_name: str = Field(default="", max_length=500)
    character_name: str = Field(default="", max_length=500)
    eso_class: str = Field(default="", max_length=120)
    build_name: str = Field(default="", max_length=500)
    gear_summary: str = Field(default="", max_length=4000)
    unresolved: str = Field(default="", max_length=4000)
    role: str = Field(default="", max_length=120)
    source_kind: str = Field(default="", max_length=120)
    source_name: str = Field(default="", max_length=500)
    source_url: str = Field(default="", max_length=2000)
    candidate_id: str = Field(default="", max_length=240)
    gear_sets: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    mundus: str = Field(default="", max_length=240)

    @field_validator("gear_sets", "skills")
    @classmethod
    def validate_collection(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for item in value:
            if not item.strip() or len(item) > 500:
                raise ValueError("generated draft collection value is invalid")
        return value


class GeneratedRosterDraftPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: str = Field(min_length=1, max_length=500)
    goal: str = Field(min_length=1, max_length=2000)
    difficulty: str = Field(default="", max_length=240)
    slots: tuple[GeneratedRosterDraftSlotPayload, ...] = Field(min_length=1)


class GeneratedRosterPrescriptionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    draft_id: int = Field(gt=0)
    slot_name: str = Field(min_length=1, max_length=120)
    prescription: dict[str, Any]
    adopted_player_name: str = Field(default="", max_length=500)
    adopted_character_name: str = Field(default="", max_length=500)
    adopted_build_name: str = Field(default="", max_length=500)


def validate_generated_roster_draft(raw: Any) -> dict[str, Any]:
    return GeneratedRosterDraftPayload.model_validate(raw).model_dump(mode="python")


def validate_generated_roster_prescription(raw: Any) -> dict[str, Any]:
    return GeneratedRosterPrescriptionPayload.model_validate(raw).model_dump(mode="python")
