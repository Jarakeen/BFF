from __future__ import annotations

from dataclasses import dataclass, replace

from .coverage_classification import (
    CoverageClassification,
    CoverageClassificationResult,
)
from .coverage_conflict import CoverageConflictReport, CoverageConflictAnalyzer
from .coverage_gap import CoverageAnalysis, CoverageGapAnalyzer
from .coverage_recommendation import (
    CoverageRecommendation,
    CoverageRecommendationAnalyzer,
    RecommendationAction,
)
from .coverage_requirement import CoverageRequirement
from .encounter_requirements import EncounterRequirementSet
from .roster_coverage import RosterCapabilityProvider, RosterCoverageAnalyzer
from .character_build.effect_relationship import ConditionContext


@dataclass(frozen=True)
class EncounterEvaluation:
    """
    Complete evaluation of one encounter requirement set against a roster.

    The result preserves the mechanical evidence, the actionable
    classifications, and the recommendation intent derived from that
    evidence. It still does not choose a specific replacement build or
    provider; that belongs to the later assignment/optimization layer.

    `classifications` contains only requirements that are currently active.

    `inactive_requirements` contains requirements whose encounter condition
    is not satisfied by the supplied condition context.
    """

    requirement_set: EncounterRequirementSet
    classifications: tuple[CoverageClassificationResult, ...]
    inactive_requirements: tuple[CoverageRequirement, ...]
    coverage_analysis: CoverageAnalysis
    conflicts: CoverageConflictReport
    recommendations: tuple[CoverageRecommendation, ...] = ()

    def classification_for_effect(
        self,
        effect_name: str,
    ) -> CoverageClassificationResult | None:
        """Return the final classification for one active requirement."""
        for classification in self.classifications:
            if classification.effect_name == effect_name:
                return classification
        return None

    def recommendation_for_effect(
        self,
        effect_name: str,
    ) -> CoverageRecommendation | None:
        """Return the recommendation intent for one active requirement."""
        for recommendation in self.recommendations:
            if recommendation.effect_name == effect_name:
                return recommendation
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
    def actionable_recommendations(self) -> tuple[CoverageRecommendation, ...]:
        """Return recommendations that imply an actual follow-up action."""
        return tuple(
            recommendation
            for recommendation in self.recommendations
            if recommendation.action.value != "no_action"
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
    - recommend a specific roster change,
    - interpret ESO-specific mechanics.

    It does produce a typed recommendation *intent* for each classification.
    The intent says what kind of action is warranted without pretending to
    know which player/build/skill/set should be changed.
    """

    def __init__(
        self,
        roster_coverage_analyzer: RosterCoverageAnalyzer | None = None,
        coverage_gap_analyzer: CoverageGapAnalyzer | None = None,
        coverage_conflict_analyzer: CoverageConflictAnalyzer | None = None,
        recommendation_analyzer: CoverageRecommendationAnalyzer | None = None,
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
        self.recommendation_analyzer = (
            recommendation_analyzer
            or CoverageRecommendationAnalyzer()
        )

    def evaluate(
        self,
        requirement_set: EncounterRequirementSet,
        roster_capabilities: dict[
            str,
            tuple[RosterCapabilityProvider, ...],
        ],
        condition_context: ConditionContext | None = None,
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
        )

        recommendations = tuple(
            self._recommend_for_encounter(classification)
            for classification in classifications
        )

        return EncounterEvaluation(
            requirement_set=requirement_set,
            classifications=classifications,
            inactive_requirements=tuple(inactive_requirements),
            coverage_analysis=coverage_analysis,
            conflicts=conflicts,
            recommendations=recommendations,
        )

    def _recommend_for_encounter(
        self,
        classification: CoverageClassificationResult,
    ) -> CoverageRecommendation:
        """
        Resolve recommendation intent in encounter context.

        The standalone recommendation analyzer deliberately treats an
        existing provider with insufficient evidence as an uptime
        investigation. At the encounter-evaluation boundary, however, a
        hard provider-count requirement is an explicit composition
        constraint: if fewer valid providers exist than the encounter
        requires, the encounter needs another qualifying provider source.

        This keeps the generic recommendation analyzer conservative while
        making the encounter result operationally faithful to its declared
        provider-count requirement.
        """
        recommendation = self.recommendation_analyzer.recommend(classification)

        if (
            classification.classification == CoverageClassification.INSUFFICIENT
            and classification.valid_provider_count > 0
            and classification.valid_provider_count < classification.required_provider_count
        ):
            missing_count = (
                classification.required_provider_count
                - classification.valid_provider_count
            )
            recommendation = replace(
                recommendation,
                action=RecommendationAction.ADD_PROVIDER,
                explanation=(
                    f"{classification.effect_name} requires "
                    f"{classification.required_provider_count} valid provider(s), "
                    f"but only {classification.valid_provider_count} qualify. "
                    f"At least {missing_count} additional qualifying provider "
                    "source(s) are needed for this encounter requirement."
                ),
            )

        return recommendation

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
