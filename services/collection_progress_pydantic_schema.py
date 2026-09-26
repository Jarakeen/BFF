from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CollectionProfilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    profile: str = Field(min_length=1, max_length=240)

    @field_validator("profile")
    @classmethod
    def normalized_profile(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValueError("profile cannot be empty")
        return cleaned


class CollectionProgressPayload(CollectionProfilePayload):
    item_id: int = Field(gt=0)
    owned: bool
    acquired_on: str = Field(default="", max_length=80)
    notes: str = Field(default="", max_length=8000)


class CollectionBatchPayload(CollectionProfilePayload):
    owned_by_id: dict[int, bool] = Field(default_factory=dict)

    @field_validator("owned_by_id")
    @classmethod
    def positive_ids(cls, value: dict[int, bool]) -> dict[int, bool]:
        if any(item_id <= 0 for item_id in value):
            raise ValueError("collection item ids must be positive")
        return value


class StickerbookBookmarkPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    profile: str = Field(min_length=1, max_length=240)
    set_id: int = Field(gt=0)
    bookmarked: bool
    note: str | None = Field(default=None, max_length=8000)

    @field_validator("profile")
    @classmethod
    def normalized_profile(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValueError("profile cannot be empty")
        return cleaned


def validate_collection_profile(profile: str) -> str:
    return CollectionProfilePayload.model_validate({"profile": profile}).profile


def validate_collection_progress(raw: Any) -> dict[str, Any]:
    return CollectionProgressPayload.model_validate(raw).model_dump(mode="json")


def validate_collection_batch(raw: Any) -> dict[str, Any]:
    return CollectionBatchPayload.model_validate(raw).model_dump(mode="python")


def validate_stickerbook_bookmark(raw: Any) -> dict[str, Any]:
    return StickerbookBookmarkPayload.model_validate(raw).model_dump(mode="python")
