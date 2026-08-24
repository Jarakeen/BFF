from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .coverage_classification import (
    CoverageClassification,
    CoverageClassificationResult,
)


class RecommendationAction(str, Enum):
    """
    Operational action implied by an actionable coverage classification.

    This describes what should be investigated or changed, not which
    specific character, build, skill, set, or gear choice should be made.
    """

    NO_ACTION = "no_action"
    ADD_PROVIDER = "add_provider"
    INCREASE_UPTIME = "increase_uptime"
    RESOLVE_CONFLICT = "resolve_conflict"
    REPLACE_PROVIDER = "replace_provider"
    VERIFY_DATA = "verify_data"


@dataclass(frozen=True)
class CoverageRecommendation:
    """
    One recommendation derived from an actionable coverage result.

    The recommendation preserves the evidence that produced it so later
    consumers do not need to reconstruct the classification.
    """

    effect_name: str
    action: RecommendationAction
    classification: CoverageClassification

    providers: tuple[str, ...] = ()
    redundant_providers: tuple[str, ...] = ()
    conflicting_providers: tuple[str, ...] = ()

    required_provider_count: int = 0
    valid_provider_count: int = 0

    explanation: str = ""


class CoverageRecommendationAnalyzer:
    """
    Convert actionable coverage classifications into recommendation
    intents.

    This layer does not choose a specific roster member, role, build,
    skill, set, or gear change.

    It identifies only the kind of action the existing evidence supports.
    """

    def recommend(
        self,
        result: CoverageClassificationResult,
    ) -> CoverageRecommendation:
        classification = result.classification

        if classification == CoverageClassification.COVERED:
            return self._recommend_no_action(result)

        if classification == CoverageClassification.REDUNDANT:
            return self._recommend_redundant(result)

        if classification == CoverageClassification.MISSING:
            return self._recommend_missing(result)

        if classification == CoverageClassification.INSUFFICIENT:
            return self._recommend_insufficient(result)

        if classification == CoverageClassification.CONFLICT:
            return self._recommend_conflict(result)

        return self._recommend_unknown(result)

    @staticmethod
    def _recommend_no_action(
        result: CoverageClassificationResult,
    ) -> CoverageRecommendation:
        return CoverageRecommendation(
            effect_name=result.effect_name,
            action=RecommendationAction.NO_ACTION,
            classification=result.classification,
            providers=result.providers,
            required_provider_count=result.required_provider_count,
            valid_provider_count=result.valid_provider_count,
            explanation=(
                f"{result.effect_name} is sufficiently covered."
            ),
        )

    @staticmethod
    def _recommend_redundant(
        result: CoverageClassificationResult,
    ) -> CoverageRecommendation:
        return CoverageRecommendation(
            effect_name=result.effect_name,
            action=RecommendationAction.NO_ACTION,
            classification=result.classification,
            providers=result.providers,
            redundant_providers=result.redundant_providers,
            required_provider_count=result.required_provider_count,
            valid_provider_count=result.valid_provider_count,
            explanation=(
                f"{result.effect_name} is covered with additional "
                "provider redundancy. No correction is required."
            ),
        )

    @staticmethod
    def _recommend_missing(
        result: CoverageClassificationResult,
    ) -> CoverageRecommendation:
        return CoverageRecommendation(
            effect_name=result.effect_name,
            action=RecommendationAction.ADD_PROVIDER,
            classification=result.classification,
            providers=result.providers,
            required_provider_count=result.required_provider_count,
            valid_provider_count=result.valid_provider_count,
            explanation=(
                f"{result.effect_name} has no valid provider. "
                "Another provider must be identified."
            ),
        )

    @staticmethod
    def _recommend_insufficient(
        result: CoverageClassificationResult,
    ) -> CoverageRecommendation:
        if result.valid_provider_count > 0:
            action = RecommendationAction.INCREASE_UPTIME
            explanation = (
                f"{result.effect_name} has valid provider coverage, "
                "but it does not satisfy the requirement. "
                "Uptime or coverage conditions should be investigated."
            )
        else:
            action = RecommendationAction.ADD_PROVIDER
            explanation = (
                f"{result.effect_name} does not have enough valid "
                "provider coverage. Another provider should be identified."
            )

        return CoverageRecommendation(
            effect_name=result.effect_name,
            action=action,
            classification=result.classification,
            providers=result.providers,
            required_provider_count=result.required_provider_count,
            valid_provider_count=result.valid_provider_count,
            explanation=explanation,
        )

    @staticmethod
    def _recommend_conflict(
        result: CoverageClassificationResult,
    ) -> CoverageRecommendation:
        return CoverageRecommendation(
            effect_name=result.effect_name,
            action=RecommendationAction.RESOLVE_CONFLICT,
            classification=result.classification,
            providers=result.providers,
            conflicting_providers=result.conflicting_providers,
            required_provider_count=result.required_provider_count,
            valid_provider_count=result.valid_provider_count,
            explanation=(
                f"{result.effect_name} has an explicit provider "
                "conflict that must be resolved."
            ),
        )

    @staticmethod
    def _recommend_unknown(
        result: CoverageClassificationResult,
    ) -> CoverageRecommendation:
        return CoverageRecommendation(
            effect_name=result.effect_name,
            action=RecommendationAction.VERIFY_DATA,
            classification=result.classification,
            providers=result.providers,
            required_provider_count=result.required_provider_count,
            valid_provider_count=result.valid_provider_count,
            explanation=(
                f"The available evidence is insufficient to safely "
                f"recommend an action for {result.effect_name}."
            ),
        )
