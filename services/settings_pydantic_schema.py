from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SettingsPayload(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    EsoLogsClientId: str = Field(default="", max_length=1000)
    BrittleDefaultActorId: str = Field(default="72", max_length=120)
    BuildsExportFolder: str = Field(default="", max_length=4000)
    FinchApiUrl: str = Field(default="", max_length=4000)
    ObsWebSocketPort: int = Field(default=4455, ge=1, le=65535)

    @field_validator("*", mode="before")
    @classmethod
    def reject_none(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("Settings values may not be null")
        return value


class AccessibilityPayload(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    ColorVisionMode: str = Field(default="colorblind_friendly", max_length=120)
    VisualTheme: str = Field(default="rylo_city_night", max_length=120)


def validate_settings_payload(raw: Any) -> dict[str, Any]:
    return SettingsPayload.model_validate(raw).model_dump(mode="json", exclude_unset=False)


def validate_accessibility_payload(raw: Any) -> dict[str, Any]:
    return AccessibilityPayload.model_validate(raw).model_dump(mode="json", exclude_unset=False)
