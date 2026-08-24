from __future__ import annotations

from dataclasses import dataclass

from .coverage_classification import CoverageClassificationResult
from .coverage_conflict import CoverageConflictReport, CoverageConflictAnalyzer
from .coverage_gap import CoverageAnalysis, CoverageGapAnalyzer
from .coverage_requirement import CoverageRequirement
from .encounter_requirements import EncounterRequirementSet
from .roster_coverage import RosterCoverageAnalyzer, RosterCapabilityProvider
from .character_build.effect_relationship import ConditionContext


@dataclass(frozen=True)
class EncounterEvaluation:
    """
    Complete evaluation of one encounter requirement set against a roster.

    This is the encounter-level composition result. The underlying
    mechanical evidence is preserved rather than reduced to classifications
    alone.

    `classifications` contains only requirements that are currently active.

    `inactive_requirements` contains requirements whose encounter condition
    is not satisfied by the supplied condition context.
    """

    requirement_set: EncounterRequirementSet

    classifications: tuple[CoverageClassificationResult, ...]

    inactive_requirements: tuple[CoverageRequirement, ...]

    coverage_analysis: CoverageAnalysis

    conflicts: CoverageConflictReport

    def classification_for_effect(
        self,
        effect_name: str,
    ) -> CoverageClassificationResult | None:
        """Return the final classification for one active requirement."""
        for classification in self.classifications:
            if classification.effect_name == effect_name:
                return classification

        return None

    @property
    def problems(self) -> tuple[CoverageClassificationResult, ...]:
        """Return active requirements that require attention."""
        return tuple(
            classification
            for classification in self.classifications
            if classification.is_actionable_problem
        )

    @property
    def satisfied(self) -> tuple[CoverageClassificationResult, ...]:
        """Return active requirements that are currently satisfied."""
        return tuple(
            classification
            for classification in self.classifications
            if classification.is_satisfied
        )

    @property
    def is_fully_covered(self) -> bool:
        """
        Whether every currently active requirement is satisfied.

        Inactive encounter requirements do not count against coverage.
        """
        return not self.problems


class EncounterEvaluator:
    """
    Compose encounter requirements with already-resolved roster capability
    evidence.

    This layer answers:

        "Given these encounter requirements and this roster capability
        evidence, what is the current state?"

    It does not:

    - resolve character builds,
    - resolve effects or procs,
    - invent encounter requirements,
    - optimize provider assignments,
    - recommend roster changes,
    - interpret ESO-specific mechanics.

    Those responsibilities remain in their respective layers.
    """

    def __init__(
        self,
        roster_coverage_analyzer: RosterCoverageAnalyzer | None = None,
        coverage_gap_analyzer: CoverageGapAnalyzer | None = None,
        coverage_conflict_analyzer: CoverageConflictAnalyzer | None = None,
    ) -> None:
        self.roster_coverage_analyzer = (
            roster_coverage_analyzer
            or RosterCoverageAnalyzer()
        )
        self.coverage_gap_analyzer = (
            coverage_gap_analyzer
            or CoverageGapAnalyzer()
        )
        self.coverage_conflict_analyzer = (
            coverage_conflict_analyzer
            or CoverageConflictAnalyzer()
        )

    def evaluate(
        self,
        requirement_set: EncounterRequirementSet,
        roster_capabilities: dict[
            str,
            tuple[RosterCapabilityProvider, ...],
        ],
        condition_context: ConditionContext | None = None,
        *,
        resilient_providers_by_effect: dict[str, tuple[str, ...]] | None = None,
        unknown_effects: frozenset[str] = frozenset(),
    ) -> EncounterEvaluation:
        """
        Evaluate one encounter requirement set against roster capabilities.

        A requirement with no condition is always active.

        A requirement with a condition is active only when that condition is
        present in the supplied ConditionContext.

        When condition_context is None, no requirement is gated. This
        preserves the same default semantics used by provider-side
        condition resolution.
        """
        active_requirements: list[CoverageRequirement] = []
        inactive_requirements: list[CoverageRequirement] = []

        for requirement in requirement_set.all():
            if self._requirement_is_active(
                requirement,
                condition_context,
            ):
                active_requirements.append(requirement)
            else:
                inactive_requirements.append(requirement)

        coverage = self.roster_coverage_analyzer.analyze(
            roster_capabilities,
        )

        coverage_analysis = self.coverage_gap_analyzer.analyze(
            coverage,
            tuple(active_requirements),
        )

        conflicts = self.coverage_conflict_analyzer.analyze(
            coverage_analysis,
        )

        classifications = coverage_analysis.classifications(
            conflicts,
            resilient_providers_by_effect=resilient_providers_by_effect,
            unknown_effects=unknown_effects,
        )

        return EncounterEvaluation(
            requirement_set=requirement_set,
            classifications=classifications,
            inactive_requirements=tuple(inactive_requirements),
            coverage_analysis=coverage_analysis,
            conflicts=conflicts,
        )

    @staticmethod
    def _requirement_is_active(
        requirement: CoverageRequirement,
        condition_context: ConditionContext | None,
    ) -> bool:
        """
        Determine whether an encounter requirement currently applies.

        Requirement conditions are intentionally simple opaque names.
        EncounterEvaluator does not interpret what a condition means; the
        supplied ConditionContext determines whether it is currently true.

        No condition means the requirement is always active.

        A missing context means no gating is requested, preserving the
        repository-wide default behavior.
        """
        if requirement.condition is None:
            return True

        if condition_context is None:
            return True

        return requirement.condition in condition_context