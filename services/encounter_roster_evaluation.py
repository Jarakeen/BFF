from __future__ import annotations

"""One-call Phase 10 orchestration for encounter requirements vs saved-build audits."""

from dataclasses import dataclass

from services.encounter_build_capability_adapter import (
    SavedBuildEncounterCapabilityAdapter,
)
from services.encounter_cleanse_method import (
    EncounterCleanseMethod,
    EncounterCleanseMethodService,
)
from services.encounter_requirement_evaluation import (
    EncounterRequirementEvaluation,
    EncounterRequirementEvaluator,
    RequirementEvaluation,
    RequirementSemantics,
)
from services.encounter_service import EncounterService
from services.saved_build_capability_service import SavedBuildCapabilityAudit


@dataclass(frozen=True)
class EncounterRosterEvaluationReport:
    """Combined requirement result plus source-backed mechanic method detail."""

    requirement_evaluation: EncounterRequirementEvaluation
    cleanse_methods: tuple[EncounterCleanseMethod, ...]

    @property
    def encounter_id(self) -> str:
        return self.requirement_evaluation.encounter_id

    @property
    def results(self) -> tuple[RequirementEvaluation, ...]:
        return self.requirement_evaluation.results

    @property
    def unknown(self) -> tuple[RequirementEvaluation, ...]:
        return self.requirement_evaluation.unknown

    @property
    def problems(self) -> tuple[RequirementEvaluation, ...]:
        return self.requirement_evaluation.problems

    @property
    def satisfied(self) -> tuple[RequirementEvaluation, ...]:
        return self.requirement_evaluation.satisfied

    @property
    def is_fully_evaluable(self) -> bool:
        return self.requirement_evaluation.is_fully_evaluable

    @property
    def is_fully_covered(self) -> bool:
        return self.requirement_evaluation.is_fully_covered


class EncounterRosterEvaluator:
    """Compose Phase 9 requirements with existing saved-build capability audits.

    This orchestrator does not assign providers or invent capability mappings.
    The adapter owns exact identity recognition; the requirement evaluator owns
    coverage classification. Canonical character identity is used for roster
    membership so display-name changes cannot create or erase provider evidence.

    Cleanse method detail is attached separately so a generic ``cleanse`` demand
    cannot be mistaken for proof that a player cleanse skill is the required method.
    """

    def __init__(
        self,
        encounter_service: EncounterService,
        build_capability_adapter: SavedBuildEncounterCapabilityAdapter,
    ) -> None:
        self._encounter_service = encounter_service
        self._adapter = build_capability_adapter
        self._evaluator = EncounterRequirementEvaluator(encounter_service)
        self._cleanse_methods = EncounterCleanseMethodService(encounter_service)

    def evaluate_saved_build_audits(
        self,
        encounter_id: str,
        audits: tuple[SavedBuildCapabilityAudit, ...],
    ) -> EncounterRosterEvaluationReport:
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
        requirement_evaluation = self._evaluator.evaluate(
            encounter_id,
            roster_members,
            evidence,
        )
        return EncounterRosterEvaluationReport(
            requirement_evaluation=requirement_evaluation,
            cleanse_methods=self._cleanse_methods.methods(encounter_id),
        )
