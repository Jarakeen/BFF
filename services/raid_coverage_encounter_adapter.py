from __future__ import annotations

"""Adapt explicit raid coverage requirements into the encounter evaluation context.

These rows are analysis/strategy requirements, not boss mechanics. The adapter keeps
that provenance explicit while translating only source-backed capability mappings
into the same EncounterRequirement contract consumed by Phase 10.
"""

from dataclasses import dataclass

from services.encounter_build_capability_adapter import EncounterCapabilityIdentityMap
from services.encounter_requirement_evaluation import RequirementSemantics
from services.encounter_service import EncounterRequirement
from services.raid_coverage_profile import RaidCoverageProfile


@dataclass(frozen=True)
class RaidCoverageEncounterAdapter:
    profile: RaidCoverageProfile

    def requirements(self, encounter_id: str) -> tuple[EncounterRequirement, ...]:
        if not encounter_id:
            raise ValueError("encounter_id must be non-empty")
        return tuple(
            EncounterRequirement(
                requirement_id=f"{encounter_id}:coverage:{row.requirement_id}",
                encounter_id=encounter_id,
                mechanic_id=f"coverage-profile:{self.profile.profile_id}",
                mechanic_name=row.display_name,
                requirement_type=row.capability_type,
                target_count=None,
                interpretation_status="configured_raid_coverage",
            )
            for row in self.profile.mapped_required
            if row.capability_type is not None
        )

    def requirement_semantics(self) -> dict[str, RequirementSemantics]:
        return {
            row.capability_type: RequirementSemantics.PROVIDER_CAPABILITY
            for row in self.profile.mapped_required
            if row.capability_type is not None
        }

    def required_provider_counts(self, encounter_id: str) -> dict[str, int]:
        return {
            requirement.requirement_id: coverage.required_provider_count
            for requirement, coverage in zip(
                self.requirements(encounter_id),
                self.profile.coverage_requirements(),
                strict=True,
            )
        }

    def capability_identity_maps(self) -> tuple[EncounterCapabilityIdentityMap, ...]:
        """Return only exact EffectVariant identity mappings already proven by the profile."""
        return tuple(
            EncounterCapabilityIdentityMap(
                capability_type=row.capability_type,
                effect_names=frozenset((row.capability_type,)),
            )
            for row in self.profile.mapped_required
            if row.capability_type is not None
        )
