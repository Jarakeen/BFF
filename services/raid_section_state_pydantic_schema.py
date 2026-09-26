from __future__ import annotations

"""Strict durable schema for explicit Live Raid / Review user state."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _LooseRecord(BaseModel):
    """Bound the known durable record while retaining older additive fields."""

    model_config = ConfigDict(extra="allow", strict=True, str_strip_whitespace=True)


class RaidRunStatePayload(_LooseRecord):
    attempt: int = Field(default=0, ge=0)
    active: bool = False
    started_at: str = Field(default="", max_length=128)
    ended_at: str = Field(default="", max_length=128)
    notes_paused: bool = False
    notes: str = Field(default="", max_length=50000)
    encounter_id: str = Field(default="", max_length=240)
    trial_id: str = Field(default="", max_length=240)
    plan_name: str = Field(default="", max_length=500)


class RaidRunEventPayload(_LooseRecord):
    timestamp: str = Field(default="", max_length=128)
    plan_id: str = Field(min_length=1, max_length=240)
    kind: str = Field(min_length=1, max_length=120)
    text: str = Field(default="", max_length=12000)
    evidence: str = Field(default="MANUAL", max_length=120)


class RaidReviewPayload(_LooseRecord):
    review_id: str = Field(default="", max_length=500)
    plan_id: str = Field(min_length=1, max_length=240)
    trial_id: str = Field(default="", max_length=240)
    plan_name: str = Field(default="", max_length=500)
    attempt: int = Field(default=0, ge=0)
    notes: str = Field(default="", max_length=50000)
    encounter_id: str = Field(default="", max_length=240)
    started_at: str = Field(default="", max_length=128)
    ended_at: str = Field(default="", max_length=128)
    created_at: str = Field(default="", max_length=128)
    updated_at: str = Field(default="", max_length=128)
    duration_seconds: int | None = Field(default=None, ge=0)


class RaidAttemptPayload(_LooseRecord):
    plan_id: str = Field(min_length=1, max_length=240)
    attempt: int = Field(default=0, ge=0)
    encounter_id: str = Field(default="", max_length=240)
    trial_id: str = Field(default="", max_length=240)
    plan_name: str = Field(default="", max_length=500)
    started_at: str = Field(default="", max_length=128)
    ended_at: str = Field(default="", max_length=128)
    duration_seconds: int | None = Field(default=None, ge=0)


class FinchRaidMapPreviewPayload(_LooseRecord):
    encounter_id: str = Field(min_length=1, max_length=240)
    encounter_name: str = Field(default="", max_length=500)
    map_label: str = Field(default="Raid Map", max_length=500)
    map_image_url: str = Field(min_length=1, max_length=4000)
    note: str = Field(default="", max_length=12000)
    content_sha256: str = Field(default="", max_length=128)


class RaidSectionStatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    human_ready: dict[str, dict[str, bool]] = Field(default_factory=dict)
    runs: dict[str, RaidRunStatePayload] = Field(default_factory=dict)
    events: list[RaidRunEventPayload] = Field(default_factory=list)
    reviews: list[RaidReviewPayload] = Field(default_factory=list)
    attempts: list[RaidAttemptPayload] = Field(default_factory=list)
    raid_map_links: dict[str, dict[str, str]] = Field(default_factory=dict)
    finch_raid_map_previews: dict[str, dict[str, FinchRaidMapPreviewPayload]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_identity_maps(self) -> "RaidSectionStatePayload":
        for collection_name, collection in (
            ("human_ready", self.human_ready),
            ("runs", self.runs),
            ("raid_map_links", self.raid_map_links),
            ("finch_raid_map_previews", self.finch_raid_map_previews),
        ):
            for key in collection:
                if not key.strip() or len(key) > 240:
                    raise ValueError(f"{collection_name} contains an invalid plan id")
        return self


def validate_raid_section_state_payload(raw: Any) -> dict[str, Any]:
    return RaidSectionStatePayload.model_validate(raw).model_dump(mode="json")
