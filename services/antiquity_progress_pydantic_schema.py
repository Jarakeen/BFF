from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AntiquityProgressEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    recovered: bool = False
    recovered_on: str = Field(default="", max_length=80)
    notes: str = Field(default="", max_length=8000)


class AntiquityProgressDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: int = Field(default=1, ge=1)
    profiles: dict[str, dict[str, AntiquityProgressEntry]] = Field(default_factory=dict)

    @field_validator("profiles")
    @classmethod
    def validate_profiles(
        cls, value: dict[str, dict[str, AntiquityProgressEntry]]
    ) -> dict[str, dict[str, AntiquityProgressEntry]]:
        seen: set[str] = set()
        for profile, entries in value.items():
            name = " ".join(str(profile).strip().split())
            if not name or len(name) > 240:
                raise ValueError("antiquity profile name is invalid")
            folded = name.casefold()
            if folded in seen:
                raise ValueError("duplicate antiquity profile name")
            seen.add(folded)
            for raw_id in entries:
                if not raw_id.isdigit() or int(raw_id) <= 0:
                    raise ValueError("antiquity progress IDs must be positive integers")
        return value


def validate_antiquity_progress_document(raw: Any) -> dict[str, Any]:
    return AntiquityProgressDocument.model_validate(raw).model_dump(mode="json")
