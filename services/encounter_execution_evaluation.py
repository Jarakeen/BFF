from __future__ import annotations

"""Phase 10 evaluation of build-independent encounter execution readiness.

This layer answers whether BFF knows *how* a generic encounter action is handled
without pretending that player execution has already occurred. Core game actions,
encounter-provided interactions, and source-backed movement/positioning handling
methods are build-independent capabilities. Player-skill requirements remain
provider questions and are not silently satisfied here.
"""

from dataclasses import dataclass

from minmax.coverage_classification import CoverageClassification
from services.encounter_cleanse_method import (
    CleanseMethod,
    CleanseMethodResolution,
    EncounterCleanseMethod,
    EncounterCleanseMethodService,
)
from services.encounter_execution_method import (
    EncounterExecutionMethod,
    EncounterExecutionMethodService,
    ExecutionMethodResolution,
)
from services.encounter_interrupt_method import (
    EncounterInterruptMethodService,
    InterruptMethod,
    InterruptMethodResolution,
)
from services.encounter_service import EncounterRequirement, EncounterService


@dataclass(frozen=True)
class ExecutionRequirementEvaluation:
    requirement_id: str
    encounter_id: str
    mechanic_id: str
    mechanic_name: str
    requirement_type: str
    classification: CoverageClassification
    handling_method: str
    interaction: str
    requires_player_build_capability: bool | None
    explanation: str

    @property
    def is_satisfied(self) -> bool:
        return self.classification in {
            CoverageClassification.COVERED,
            CoverageClassification.REDUNDANT,
            CoverageClassification.RESILIENT,
        }

    @property
    def is_actionable_problem(self) -> bool:
        return self.classification in {
            CoverageClassification.MISSING,
            CoverageClassification.INSUFFICIENT,
            CoverageClassification.CONFLICT,
        }


@dataclass(frozen=True)
class EncounterExecutionEvaluation:
    encounter_id: str
    results: tuple[ExecutionRequirementEvaluation, ...]

    @property
    def unknown(self) -> tuple[ExecutionRequirementEvaluation, ...]:
        return tuple(
            row for row in self.results
            if row.classification == CoverageClassification.UNKNOWN
        )

    @property
    def problems(self) -> tuple[ExecutionRequirementEvaluation, ...]:
        return tuple(row for row in self.results if row.is_actionable_problem)

    @property
    def satisfied(self) -> tuple[ExecutionRequirementEvaluation, ...]:
        return tuple(row for row in self.results if row.is_satisfied)

    @property
    def is_fully_evaluable(self) -> bool:
        return not self.unknown

    @property
    def is_fully_ready(self) -> bool:
        return self.is_fully_evaluable and not self.problems


class EncounterExecutionEvaluator:
    """Resolve generic execution requirements without inventing player performance."""

    def __init__(self, encounter_service: EncounterService) -> None:
        self._encounter_service = encounter_service
        self._cleanse_methods = EncounterCleanseMethodService(encounter_service)
        self._interrupt_methods = EncounterInterruptMethodService(encounter_service)
        self._execution_methods = EncounterExecutionMethodService(encounter_service)

    @staticmethod
    def _cleanse_methods_by_requirement(
        requirements: tuple[EncounterRequirement, ...],
        methods: tuple[EncounterCleanseMethod, ...],
    ) -> dict[str, EncounterCleanseMethod]:
        """Join cleanse methods to requirements without fuzzy mechanic matching."""
        cleanse_requirements = tuple(
            requirement
            for requirement in requirements
            if requirement.requirement_type == "cleanse"
        )
        by_requirement_id: dict[str, EncounterCleanseMethod] = {}
        methods_by_name = {method.mechanic_name: method for method in methods}

        unmatched_requirements: list[EncounterRequirement] = []
        matched_fact_ids: set[str] = set()
        for requirement in cleanse_requirements:
            method = methods_by_name.get(requirement.mechanic_name)
            if method is None:
                unmatched_requirements.append(requirement)
                continue
            by_requirement_id[requirement.requirement_id] = method
            matched_fact_ids.add(method.fact_id)

        unmatched_methods = tuple(
            method for method in methods if method.fact_id not in matched_fact_ids
        )
        if len(unmatched_requirements) == 1 and len(unmatched_methods) == 1:
            by_requirement_id[unmatched_requirements[0].requirement_id] = unmatched_methods[0]

        return by_requirement_id

    def evaluate(self, encounter_id: str) -> EncounterExecutionEvaluation:
        requirements = self._encounter_service.requirements(encounter_id)
        cleanse_methods = self._cleanse_methods.methods(encounter_id)
        cleanse_by_requirement_id = self._cleanse_methods_by_requirement(
            requirements,
            cleanse_methods,
        )
        interrupt_by_name = {
            row.mechanic_name: row
            for row in self._interrupt_methods.methods(encounter_id)
        }
        execution_by_key: dict[tuple[str, str], EncounterExecutionMethod] = {}
        execution_conflicts: set[tuple[str, str]] = set()
        for row in self._execution_methods.methods(encounter_id):
            key = (row.mechanic_name, row.requirement_type)
            if key in execution_by_key:
                previous = execution_by_key[key]
                if previous.method != row.method or previous.resolution != row.resolution:
                    execution_conflicts.add(key)
                continue
            execution_by_key[key] = row

        rows = tuple(
            self._evaluate_requirement(
                requirement,
                cleanse_by_requirement_id=cleanse_by_requirement_id,
                interrupt_by_name=interrupt_by_name,
                execution_by_key=execution_by_key,
                execution_conflicts=execution_conflicts,
            )
            for requirement in requirements
        )
        return EncounterExecutionEvaluation(encounter_id=encounter_id, results=rows)

    @staticmethod
    def _unknown(requirement: EncounterRequirement, explanation: str) -> ExecutionRequirementEvaluation:
        return ExecutionRequirementEvaluation(
            requirement_id=requirement.requirement_id,
            encounter_id=requirement.encounter_id,
            mechanic_id=requirement.mechanic_id,
            mechanic_name=requirement.mechanic_name,
            requirement_type=requirement.requirement_type,
            classification=CoverageClassification.UNKNOWN,
            handling_method="",
            interaction="",
            requires_player_build_capability=None,
            explanation=explanation,
        )

    def _evaluate_requirement(
        self,
        requirement: EncounterRequirement,
        *,
        cleanse_by_requirement_id: dict[str, EncounterCleanseMethod],
        interrupt_by_name: dict,
        execution_by_key: dict[tuple[str, str], EncounterExecutionMethod],
        execution_conflicts: set[tuple[str, str]],
    ) -> ExecutionRequirementEvaluation:
        if requirement.requirement_type in {"movement", "positioning"}:
            key = (requirement.mechanic_name, requirement.requirement_type)
            if key in execution_conflicts:
                return ExecutionRequirementEvaluation(
                    requirement.requirement_id,
                    requirement.encounter_id,
                    requirement.mechanic_id,
                    requirement.mechanic_name,
                    requirement.requirement_type,
                    CoverageClassification.CONFLICT,
                    "",
                    "",
                    False,
                    "Conflicting structured evidence exists for the execution handling method.",
                )
            method = execution_by_key.get(key)
            if method is None:
                return self._unknown(
                    requirement,
                    "The encounter requires execution/positioning, but Phase 10 has no "
                    "source-backed handling method for this requirement.",
                )
            if method.resolution == ExecutionMethodResolution.CONFLICTING:
                return ExecutionRequirementEvaluation(
                    requirement.requirement_id,
                    requirement.encounter_id,
                    requirement.mechanic_id,
                    requirement.mechanic_name,
                    requirement.requirement_type,
                    CoverageClassification.CONFLICT,
                    "",
                    "",
                    False,
                    "Conflicting source evidence exists for the execution handling method.",
                )
            if method.resolution != ExecutionMethodResolution.RESOLVED or method.method is None:
                return self._unknown(requirement, "Execution handling method is unresolved.")
            return ExecutionRequirementEvaluation(
                requirement.requirement_id,
                requirement.encounter_id,
                requirement.mechanic_id,
                requirement.mechanic_name,
                requirement.requirement_type,
                CoverageClassification.COVERED,
                method.method.value,
                method.interaction,
                False,
                "A coarse build-independent handling method is source-backed. This proves "
                "the mechanic is understood, not that players will execute the strategy correctly.",
            )

        if requirement.requirement_type == "cleanse":
            method = cleanse_by_requirement_id.get(requirement.requirement_id)
            if method is None:
                return self._unknown(requirement, "Cleanse method is unresolved.")
            if method.resolution == CleanseMethodResolution.CONFLICTING:
                return ExecutionRequirementEvaluation(
                    requirement.requirement_id,
                    requirement.encounter_id,
                    requirement.mechanic_id,
                    requirement.mechanic_name,
                    requirement.requirement_type,
                    CoverageClassification.CONFLICT,
                    "",
                    "",
                    None,
                    "Conflicting source evidence exists for the cleanse method.",
                )
            if method.resolution != CleanseMethodResolution.RESOLVED or method.method is None:
                return self._unknown(requirement, "Cleanse method is unresolved.")
            if method.method in {CleanseMethod.CORE_ACTION, CleanseMethod.ENCOUNTER_INTERACTION}:
                return ExecutionRequirementEvaluation(
                    requirement.requirement_id,
                    requirement.encounter_id,
                    requirement.mechanic_id,
                    requirement.mechanic_name,
                    requirement.requirement_type,
                    CoverageClassification.COVERED,
                    method.method.value,
                    method.interaction,
                    False,
                    "The handling method is build-independent and source-backed. "
                    "This proves roster capability availability, not successful player execution.",
                )
            if method.method in {CleanseMethod.SELF_SKILL, CleanseMethod.GROUP_SKILL}:
                return ExecutionRequirementEvaluation(
                    requirement.requirement_id,
                    requirement.encounter_id,
                    requirement.mechanic_id,
                    requirement.mechanic_name,
                    requirement.requirement_type,
                    CoverageClassification.UNKNOWN,
                    method.method.value,
                    method.interaction,
                    True,
                    "The cleanse requires a player build capability; provider coverage must be evaluated separately.",
                )
            return ExecutionRequirementEvaluation(
                requirement.requirement_id,
                requirement.encounter_id,
                requirement.mechanic_id,
                requirement.mechanic_name,
                requirement.requirement_type,
                CoverageClassification.CONFLICT,
                method.method.value,
                method.interaction,
                False,
                "Encounter requires cleansing but explicit evidence classifies the method as uncleansable.",
            )

        if requirement.requirement_type == "interrupt":
            method = interrupt_by_name.get(requirement.mechanic_name)
            if method is None:
                return self._unknown(requirement, "Interrupt method is unresolved.")
            if method.resolution == InterruptMethodResolution.CONFLICTING:
                return ExecutionRequirementEvaluation(
                    requirement.requirement_id,
                    requirement.encounter_id,
                    requirement.mechanic_id,
                    requirement.mechanic_name,
                    requirement.requirement_type,
                    CoverageClassification.CONFLICT,
                    "",
                    "",
                    None,
                    "Conflicting source evidence exists for the interrupt method.",
                )
            if method.resolution != InterruptMethodResolution.RESOLVED or method.method is None:
                return self._unknown(requirement, "Interrupt method is unresolved.")
            if method.method in {InterruptMethod.CORE_BASH, InterruptMethod.ENCOUNTER_INTERACTION}:
                return ExecutionRequirementEvaluation(
                    requirement.requirement_id,
                    requirement.encounter_id,
                    requirement.mechanic_id,
                    requirement.mechanic_name,
                    requirement.requirement_type,
                    CoverageClassification.COVERED,
                    method.method.value,
                    method.interaction,
                    False,
                    "The interrupt method is build-independent and source-backed. "
                    "This proves roster capability availability, not successful player execution.",
                )
            if method.method == InterruptMethod.PLAYER_SKILL:
                return ExecutionRequirementEvaluation(
                    requirement.requirement_id,
                    requirement.encounter_id,
                    requirement.mechanic_id,
                    requirement.mechanic_name,
                    requirement.requirement_type,
                    CoverageClassification.UNKNOWN,
                    method.method.value,
                    method.interaction,
                    True,
                    "The interrupt requires a player build capability; provider coverage must be evaluated separately.",
                )
            return ExecutionRequirementEvaluation(
                requirement.requirement_id,
                requirement.encounter_id,
                requirement.mechanic_id,
                requirement.mechanic_name,
                requirement.requirement_type,
                CoverageClassification.CONFLICT,
                method.method.value,
                method.interaction,
                False,
                "Encounter requires an interrupt but explicit evidence classifies the mechanic as uninterruptible.",
            )

        return self._unknown(
            requirement,
            "No Phase 10 execution semantics exist for this requirement type.",
        )
