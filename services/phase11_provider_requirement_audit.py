from __future__ import annotations

"""Read-only Phase 11 audit for real provider-requirement readiness.

Phase 11 can only validate provider assignment against requirements that already
exist in the canonical encounter service and are explicitly mapped to
``PROVIDER_CAPABILITY`` semantics. Generic movement, positioning, cleanse, and
interrupt requirements remain compliance demands and must not be promoted merely
because a roster member happens to own a matching skill.
"""

from dataclasses import dataclass

from services.encounter_requirement_evaluation import (
    EncounterRequirementEvaluator,
    RequirementSemantics,
)
from services.encounter_service import EncounterService


@dataclass(frozen=True)
class Phase11ProviderRequirementInventory:
    encounter_count: int
    requirement_count: int
    provider_requirement_ids: tuple[str, ...]
    compliance_requirement_ids: tuple[str, ...]
    unknown_requirement_ids: tuple[str, ...]

    @property
    def provider_requirement_count(self) -> int:
        return len(self.provider_requirement_ids)

    @property
    def compliance_requirement_count(self) -> int:
        return len(self.compliance_requirement_ids)

    @property
    def unknown_requirement_count(self) -> int:
        return len(self.unknown_requirement_ids)

    @property
    def real_provider_validation_ready(self) -> bool:
        """True only when at least one real canonical provider requirement exists."""
        return self.provider_requirement_count > 0


class Phase11ProviderRequirementAudit:
    """Inventory canonical encounter requirements by their Phase 10 semantics."""

    def __init__(
        self,
        encounter_service: EncounterService,
        evaluator: EncounterRequirementEvaluator | None = None,
    ) -> None:
        self._encounter_service = encounter_service
        self._evaluator = evaluator or EncounterRequirementEvaluator(encounter_service)

    def audit(self) -> Phase11ProviderRequirementInventory:
        provider_ids: list[str] = []
        compliance_ids: list[str] = []
        unknown_ids: list[str] = []
        requirement_count = 0

        encounter_ids = self._encounter_service.encounter_ids()
        for encounter_id in encounter_ids:
            for requirement in self._encounter_service.requirements(encounter_id):
                requirement_count += 1
                semantics = self._evaluator.semantics_for(requirement.requirement_type)
                if semantics == RequirementSemantics.PROVIDER_CAPABILITY:
                    provider_ids.append(requirement.requirement_id)
                elif semantics == RequirementSemantics.COMPLIANCE:
                    compliance_ids.append(requirement.requirement_id)
                else:
                    unknown_ids.append(requirement.requirement_id)

        return Phase11ProviderRequirementInventory(
            encounter_count=len(encounter_ids),
            requirement_count=requirement_count,
            provider_requirement_ids=tuple(provider_ids),
            compliance_requirement_ids=tuple(compliance_ids),
            unknown_requirement_ids=tuple(unknown_ids),
        )
