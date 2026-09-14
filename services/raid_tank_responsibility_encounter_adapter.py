from __future__ import annotations

"""Adapt configured raid Tank responsibilities into Phase 10 provider requirements."""

from dataclasses import dataclass

from services.encounter_requirement_evaluation import RequirementSemantics
from services.encounter_service import EncounterRequirement
from services.raid_tank_responsibility_profile import RaidTankResponsibilityProfile


@dataclass(frozen=True)
class RaidTankResponsibilityEncounterAdapter:
    profile: RaidTankResponsibilityProfile

    def requirements(self, encounter_id: str) -> tuple[EncounterRequirement, ...]:
        resolved = str(encounter_id or "").strip()
        if not resolved:
            raise ValueError("encounter_id must be non-empty")
        return tuple(
            EncounterRequirement(
                requirement_id=f"{resolved}:tank:{row.requirement_id}",
                encounter_id=resolved,
                mechanic_id=f"raid-tank-profile:{self.profile.profile_id}",
                mechanic_name=row.display_name,
                requirement_type=row.capability_type,
                target_count=None,
                interpretation_status="configured_raid_tank_responsibility",
            )
            for row in self.profile.requirements
        )

    def requirement_semantics(self) -> dict[str, RequirementSemantics]:
        return {
            row.capability_type: RequirementSemantics.PROVIDER_CAPABILITY
            for row in self.profile.requirements
        }

    def required_provider_counts(self, encounter_id: str) -> dict[str, int]:
        return {
            requirement.requirement_id: row.required_provider_count
            for requirement, row in zip(
                self.requirements(encounter_id),
                self.profile.requirements,
                strict=True,
            )
        }

    @property
    def capability_types(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(row.capability_type for row in self.profile.requirements))


__all__ = ["RaidTankResponsibilityEncounterAdapter"]
