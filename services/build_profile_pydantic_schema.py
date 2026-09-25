from __future__ import annotations

"""Pydantic boundary for additive Builds profile metadata."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.build_model import ARMOR_TRAITS, JEWELRY_TRAITS

_ARMOR_TRAITS = {str(value).strip().casefold() for value in ARMOR_TRAITS if str(value).strip()}
_JEWELRY_TRAITS = {str(value).strip().casefold() for value in JEWELRY_TRAITS if str(value).strip()}
_ARMOR_WEIGHTS = {"light", "medium", "heavy"}


class BuildProfilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    quality: str = Field(default="Gold", min_length=1, max_length=40)
    item_level: str = Field(default="CP160", min_length=1, max_length=40)
    enchantment_tier: str = Field(default="Truly Superb", min_length=1, max_length=80)
    armor_trait: str = Field(default="", max_length=80)
    armor_weight: str = Field(default="", max_length=40)
    armor_enchant: str = Field(default="", max_length=160)
    jewelry_trait: str = Field(default="", max_length=80)
    jewelry_enchant: str = Field(default="", max_length=160)
    favorite: bool = False
    archived: bool = False
    ownership: str = "mine"
    source_owner: str = Field(default="", max_length=200)
    source_template_id: str = Field(default="", max_length=200)

    @field_validator("armor_trait")
    @classmethod
    def valid_armor_trait(cls, value: str) -> str:
        if value and value.casefold() not in _ARMOR_TRAITS:
            raise ValueError(f"unknown armor trait: {value!r}")
        return value

    @field_validator("armor_weight")
    @classmethod
    def valid_armor_weight(cls, value: str) -> str:
        if value and value.casefold() not in _ARMOR_WEIGHTS:
            raise ValueError(f"unknown armor weight: {value!r}")
        return value

    @field_validator("jewelry_trait")
    @classmethod
    def valid_jewelry_trait(cls, value: str) -> str:
        if value and value.casefold() not in _JEWELRY_TRAITS:
            raise ValueError(f"unknown jewelry trait: {value!r}")
        return value

    @field_validator("ownership")
    @classmethod
    def valid_ownership(cls, value: str) -> str:
        normalized = value.casefold()
        if normalized not in {"mine", "team"}:
            raise ValueError("ownership must be mine or team")
        return normalized


def validate_build_profile_payload(raw: Any) -> dict[str, Any]:
    return BuildProfilePayload.model_validate(raw).model_dump(mode="python")


__all__ = ["BuildProfilePayload", "validate_build_profile_payload"]
