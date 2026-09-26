from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RotationArtifactRecord(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)
    actions: list[dict[str, Any]] = Field(min_length=1)


class RotationArtifactDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: int = Field(ge=1)
    rotations: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @field_validator("rotations")
    @classmethod
    def validate_rotations(cls, value: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        seen: set[str] = set()
        for build_id, artifact in value.items():
            identity = str(build_id).strip()
            if not identity or len(identity) > 240:
                raise ValueError("rotation build_id is invalid")
            folded = identity.casefold()
            if folded in seen:
                raise ValueError("duplicate rotation build_id")
            seen.add(folded)
            RotationArtifactRecord.model_validate(artifact)
        return value


class PerformanceFocusGoalPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    Name: str = Field(min_length=1, max_length=240)
    TargetPercent: float = Field(ge=0, le=100)
    CurrentPercent: float | None = Field(default=None, ge=0, le=100)
    Source: str = Field(default="Custom", max_length=240)
    ReportCode: str = Field(default="", max_length=240)
    FightId: str = Field(default="", max_length=240)
    FightName: str = Field(default="", max_length=500)
    ActorLabel: str = Field(default="", max_length=500)
    Role: str = Field(default="", max_length=120)
    EvidenceNote: str = Field(default="", max_length=8000)


class PerformanceFocusDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    Goals: list[PerformanceFocusGoalPayload] = Field(default_factory=list, max_length=8)


def validate_rotation_artifact_document(raw: Any) -> dict[str, Any]:
    return RotationArtifactDocument.model_validate(raw).model_dump(mode="json")


def validate_performance_focus_document(raw: Any) -> dict[str, Any]:
    return PerformanceFocusDocument.model_validate(raw).model_dump(mode="json")
