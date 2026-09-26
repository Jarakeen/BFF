from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CompMakerTemplatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    template_id: str = Field(min_length=1, max_length=240)
    name: str = Field(min_length=1, max_length=240)
    role: str = Field(default="", max_length=120)
    eso_class: str = Field(default="", max_length=120)
    gear_sets: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    mundus: str = Field(default="", max_length=240)
    notes: str = Field(default="", max_length=8000)
    source_build_id: str = Field(default="", max_length=240)
    source_plan_name: str = Field(default="", max_length=500)
    source_seat_id: str = Field(default="", max_length=120)

    @field_validator("gear_sets", "skills")
    @classmethod
    def validate_unique_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        for item in value:
            clean = item.strip()
            if not clean or len(clean) > 500:
                raise ValueError("template collection value is invalid")
            key = clean.casefold()
            if key in seen:
                raise ValueError("template collection values must be unique")
            seen.add(key)
        return value


class PositionTimelineItemPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    item_id: str = Field(min_length=1, max_length=500)
    family: str = Field(max_length=120)
    kind: str = Field(max_length=120)
    label: str = Field(max_length=500)
    x: float
    y: float
    radius: float = Field(default=0.0, ge=0)
    visible: bool = True


class PositionTimelineStepPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: str = Field(min_length=1, max_length=500)
    note: str = Field(default="", max_length=8000)
    duration_seconds: float = Field(ge=0.2, le=30.0)
    items: list[PositionTimelineItemPayload] = Field(default_factory=list)


class PositionTimelineDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: int = Field(ge=1)
    steps: list[PositionTimelineStepPayload] = Field(default_factory=list)


def validate_comp_maker_template(raw: Any) -> dict[str, Any]:
    return CompMakerTemplatePayload.model_validate(raw).model_dump(mode="python")


def validate_position_timeline_document(raw: Any) -> dict[str, Any]:
    return PositionTimelineDocument.model_validate(raw).model_dump(mode="json")
