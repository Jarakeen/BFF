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
    """One recommendation derived from an actionable coverage result."""

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
    Convert coverage classifications into safe recommendation intents.

    This layer never selects a specific player/build/skill/set. It only
    states the kind of follow-up action justified by the evidence already
    resolved by the coverage engine.
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
    def _base(
        result: CoverageClassificationResult,
        action: RecommendationAction,
        explanation: str,
        *,
        redundant_providers: tuple[str, ...] = (),
        conflicting_providers: tuple[str, ...] = (),
    ) -> CoverageRecommendation:
        return CoverageRecommendation(
            effect_name=result.effect_name,
            action=action,
            classification=result.classification,
            providers=result.providers,
            redundant_providers=redundant_providers,
            conflicting_providers=conflicting_providers,
            required_provider_count=result.required_provider_count,
            valid_provider_count=result.valid_provider_count,
            explanation=explanation,
        )

    @classmethod
    def _recommend_no_action(cls, result):
        return cls._base(
            result,
            RecommendationAction.NO_ACTION,
            f"{result.effect_name} is sufficiently covered.",
        )

    @classmethod
    def _recommend_redundant(cls, result):
        return cls._base(
            result,
            RecommendationAction.NO_ACTION,
            f"{result.effect_name} is covered with additional provider "
            "redundancy. No correction is required.",
            redundant_providers=result.redundant_providers,
        )

    @classmethod
    def _recommend_missing(cls, result):
        return cls._base(
            result,
            RecommendationAction.ADD_PROVIDER,
            f"{result.effect_name} has no valid provider. "
            "Another provider must be identified.",
        )

    @classmethod
    def _recommend_insufficient(cls, result):
        missing_count = max(
            0,
            result.required_provider_count - result.valid_provider_count,
        )

        if missing_count:
            explanation = (
                f"{result.effect_name} requires "
                f"{result.required_provider_count} valid provider(s), "
                f"but only {result.valid_provider_count} qualify. "
                f"At least {missing_count} additional qualifying provider "
                "source(s) are needed."
            )
            action = RecommendationAction.ADD_PROVIDER
        else:
            # Defensive fallback for future classification rules. If a
            # future analyzer marks a result insufficient without a provider
            # count deficit, do not invent an optimization claim.
            explanation = (
                f"{result.effect_name} is insufficiently covered. "
                "The supporting coverage conditions should be investigated."
            )
            action = RecommendationAction.VERIFY_DATA

        return cls._base(result, action, explanation)

    @classmethod
    def _recommend_conflict(cls, result):
        return cls._base(
            result,
            RecommendationAction.RESOLVE_CONFLICT,
            f"{result.effect_name} has an explicit provider conflict "
            "that must be resolved.",
            conflicting_providers=result.conflicting_providers,
        )

    @classmethod
    def _recommend_unknown(cls, result):
        return cls._base(
            result,
            RecommendationAction.VERIFY_DATA,
            f"The available evidence is insufficient to safely "
            f"recommend an action for {result.effect_name}.",
        )
