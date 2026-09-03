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
from services.encounter_difficulty import EncounterDifficulty, normalize_encounter_difficulty
from services.encounter_execution_difficulty import DifficultyAwareEncounterExecutionEvaluator
from services.encounter_execution_evaluation import EncounterExecutionEvaluation
from services.encounter_interrupt_method import (
    EncounterInterruptMethod,
    EncounterInterruptMethodService,
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
    """Combined provider, execution, and source-backed mechanic-method results."""

    requirement_evaluation: EncounterRequirementEvaluation
    execution_evaluation: EncounterExecutionEvaluation
    cleanse_methods: tuple[EncounterCleanseMethod, ...]
    interrupt_methods: tuple[EncounterInterruptMethod, ...]
    difficulty: EncounterDifficulty = EncounterDifficulty.VETERAN

    @property
    def encounter_id(self) -> str:
        return self.requirement_evaluation.encounter_id

    @property
    def results(self) -> tuple[RequirementEvaluation, ...]:
        """Backward-compatible raw requirement classifications."""
        return self.requirement_evaluation.results

    @property
    def unknown(self) -> tuple[RequirementEvaluation, ...]:
        """Backward-compatible raw requirement UNKNOWN rows."""
        return self.requirement_evaluation.unknown

    @property
    def problems(self) -> tuple[RequirementEvaluation, ...]:
        return self.requirement_evaluation.problems

    @property
    def satisfied(self) -> tuple[RequirementEvaluation, ...]:
        return self.requirement_evaluation.satisfied

    @property
    def provider_results(self) -> tuple[RequirementEvaluation, ...]:
        """Requirements whose final state must come from roster/provider evidence.

        Generic compliance rows are excluded because the execution evaluator owns
        their final handling readiness. Unknown requirement semantics remain here
        so unsupported requirement types cannot disappear from the overall result.
        """
        return tuple(
            row
            for row in self.requirement_evaluation.results
            if row.semantics != RequirementSemantics.COMPLIANCE
        )

    @property
    def is_fully_evaluable(self) -> bool:
        provider_evaluable = all(
            row.classification.value != "unknown"
            for row in self.provider_results
        )
        return provider_evaluable and self.execution_evaluation.is_fully_evaluable

    @property
    def is_fully_covered(self) -> bool:
        provider_covered = all(row.is_satisfied for row in self.provider_results)
        return (
            self.is_fully_evaluable
            and provider_covered
            and self.execution_evaluation.is_fully_ready
        )


class EncounterRosterEvaluator:
    """Compose Phase 9 demands with saved-build and execution capability evidence.

    This orchestrator does not assign providers or invent capability mappings.
    Canonical character identity is used for roster membership. Provider coverage,
    difficulty-aware execution readiness, cleanse methods, and interrupt methods
    are returned together so callers do not have to reinterpret generic mechanics.
    """

    def __init__(
        self,
        encounter_service: EncounterService,
        build_capability_adapter: SavedBuildEncounterCapabilityAdapter,
    ) -> None:
        self._encounter_service = encounter_service
        self._adapter = build_capability_adapter
        self._evaluator = EncounterRequirementEvaluator(encounter_service)
        self._execution_evaluator = DifficultyAwareEncounterExecutionEvaluator(encounter_service)
        self._cleanse_methods = EncounterCleanseMethodService(encounter_service)
        self._interrupt_methods = EncounterInterruptMethodService(encounter_service)

    def evaluate_saved_build_audits(
        self,
        encounter_id: str,
        audits: tuple[SavedBuildCapabilityAudit, ...],
        difficulty: EncounterDifficulty | str = EncounterDifficulty.VETERAN,
    ) -> EncounterRosterEvaluationReport:
        selected_difficulty = normalize_encounter_difficulty(difficulty)
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
            execution_evaluation=self._execution_evaluator.evaluate(
                encounter_id,
                selected_difficulty,
            ),
            cleanse_methods=self._cleanse_methods.methods(encounter_id),
            interrupt_methods=self._interrupt_methods.methods(encounter_id),
            difficulty=selected_difficulty,
        )
