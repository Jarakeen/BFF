from __future__ import annotations

"""Explicit raid Tank responsibility policy above canonical encounter mechanics."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RaidTankResponsibilityRequirement:
    requirement_id: str
    display_name: str
    capability_type: str
    required_provider_count: int = 1
    source: str = ""

    def __post_init__(self) -> None:
        for field_name in ("requirement_id", "display_name", "capability_type", "source"):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"raid Tank responsibility {field_name} must be non-empty")
            object.__setattr__(self, field_name, value)
        count = int(self.required_provider_count)
        if count < 1:
            raise ValueError("raid Tank responsibility required_provider_count must be positive")
        object.__setattr__(self, "required_provider_count", count)


@dataclass(frozen=True)
class RaidTankResponsibilityProfile:
    profile_id: str
    requirements: tuple[RaidTankResponsibilityRequirement, ...]

    def __post_init__(self) -> None:
        profile_id = str(self.profile_id or "").strip()
        if not profile_id:
            raise ValueError("raid Tank responsibility profile_id must be non-empty")
        object.__setattr__(self, "profile_id", profile_id)
        rows = tuple(self.requirements)
        ids = [row.requirement_id for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError("raid Tank responsibility profile cannot duplicate requirement_id")
        object.__setattr__(self, "requirements", rows)


DEFAULT_RAID_TANK_RESPONSIBILITY_PROFILE = RaidTankResponsibilityProfile(
    profile_id="default_raid_tank_responsibility",
    requirements=(
        RaidTankResponsibilityRequirement(
            requirement_id="boss_taunt",
            display_name="Boss Taunt Ownership",
            capability_type="taunt",
            required_provider_count=1,
            source=(
                "Configured organized-raid responsibility only; capability proof comes from "
                "canonical slotted-skill TAUNT utility evidence. Encounter-specific timing and "
                "continuous ownership semantics remain separate reviewed rotation policy."
            ),
        ),
    ),
)


__all__ = [
    "DEFAULT_RAID_TANK_RESPONSIBILITY_PROFILE",
    "RaidTankResponsibilityProfile",
    "RaidTankResponsibilityRequirement",
]
