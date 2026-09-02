from __future__ import annotations

"""One-call Phase 10 orchestration for encounter requirements vs saved-build audits."""

from services.encounter_build_capability_adapter import (
    SavedBuildEncounterCapabilityAdapter,
)
from services.encounter_requirement_evaluation import (
    EncounterRequirementEvaluation,
    EncounterRequirementEvaluator,
    RequirementSemantics,
)
from services.encounter_service import EncounterService
from services.saved_build_capability_service import SavedBuildCapabilityAudit


class EncounterRosterEvaluator:
    """Compose Phase 9 requirements with existing saved-build capability audits.

    This orchestrator does not assign providers or invent capability mappings.
    The adapter owns exact identity recognition; the requirement evaluator owns
    coverage classification. Canonical character identity is used for roster
    membership so display-name changes cannot create or erase provider evidence.
    """

    def __init__(
        self,
        encounter_service: EncounterService,
        build_capability_adapter: SavedBuildEncounterCapabilityAdapter,
    ) -> None:
        self._encounter_service = encounter_service
        self._adapter = build_capability_adapter
        self._evaluator = EncounterRequirementEvaluator(encounter_service)

    def evaluate_saved_build_audits(
        self,
        encounter_id: str,
        audits: tuple[SavedBuildCapabilityAudit, ...],
    ) -> EncounterRequirementEvaluation:
        roster_members = tuple(self._adapter.member_id(audit) for audit in audits)
        if len(roster_members) != len(set(roster_members)):
            raise ValueError(
                "saved-build roster must resolve to unique member identities; "
                "select one authoritative build per roster member"
            )

        provider_capabilities = tuple(
            dict.fromkeys(
                requirement.requirement_type
                for requirement in self._encounter_service.requirements(encounter_id)
                if self._evaluator.semantics_for(requirement.requirement_type)
                == RequirementSemantics.PROVIDER_CAPABILITY
            )
        )
        evidence = self._adapter.evidence_for(audits, provider_capabilities)
        return self._evaluator.evaluate(encounter_id, roster_members, evidence)
