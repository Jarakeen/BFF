from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from services.rotation_candidate_effect_obligation_service import (
    RotationEffectObligationRankingResult,
)
from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_support_cadence_evaluation_service import (
    RotationSupportCadenceEvaluatedCandidate,
)


@dataclass(frozen=True)
class RotationSupportCadenceRecommendationCandidate:
    """Ranked cadence candidate joined back to its complete plan and evidence."""

    evaluated: RotationSupportCadenceEvaluatedCandidate
    ranking: RotationEffectObligationRankingResult

    @property
    def candidate_id(self) -> str:
        return self.evaluated.candidate_id

    @property
    def eligible(self) -> bool:
        return self.ranking.tier is RotationCandidateTier.ELIGIBLE

    @property
    def rationale(self) -> str:
        return self.evaluated.rationale

    @property
    def reasons(self) -> tuple[str, ...]:
        return self.ranking.reasons


@dataclass(frozen=True)
class RotationSupportCadenceRecommendationResult:
    """Deterministic recommendation view over already-ranked cadence candidates."""

    ordered: tuple[RotationSupportCadenceRecommendationCandidate, ...]
    recommended: RotationSupportCadenceRecommendationCandidate | None

    @property
    def has_eligible_candidate(self) -> bool:
        return self.recommended is not None


class RotationSupportCadenceRecommendationService:
    """Join final ranking output back to complete cadence candidate evidence.

    This service does not re-rank or invent policy. It trusts the existing effect-
    obligation ranking order, verifies that it contains the exact evaluated
    candidate set, and exposes the first eligible result as the recommendation.
    When every candidate is ineligible, ``recommended`` is ``None`` rather than
    silently blessing the least-bad failure.
    """

    def recommend(
        self,
        *,
        evaluated: tuple[RotationSupportCadenceEvaluatedCandidate, ...],
        ranking: tuple[RotationEffectObligationRankingResult, ...],
    ) -> RotationSupportCadenceRecommendationResult:
        if not evaluated and not ranking:
            return RotationSupportCadenceRecommendationResult(ordered=(), recommended=None)

        by_id = self._evaluated_by_id(evaluated)
        self._validate_ranking(ranking, expected=set(by_id))

        ordered = tuple(
            RotationSupportCadenceRecommendationCandidate(
                evaluated=by_id[item.candidate_id.casefold()],
                ranking=item,
            )
            for item in ranking
        )
        recommended = next((item for item in ordered if item.eligible), None)
        return RotationSupportCadenceRecommendationResult(
            ordered=ordered,
            recommended=recommended,
        )

    @staticmethod
    def _evaluated_by_id(
        evaluated: tuple[RotationSupportCadenceEvaluatedCandidate, ...],
    ) -> Mapping[str, RotationSupportCadenceEvaluatedCandidate]:
        by_id: dict[str, RotationSupportCadenceEvaluatedCandidate] = {}
        for item in evaluated:
            candidate_id = str(item.candidate_id or "").strip()
            if not candidate_id:
                raise ValueError("evaluated support cadence candidate_id must be non-empty")
            key = candidate_id.casefold()
            if key in by_id:
                raise ValueError(
                    f"duplicate evaluated support cadence candidate_id: {candidate_id!r}"
                )
            by_id[key] = item
        return by_id

    @staticmethod
    def _validate_ranking(
        ranking: tuple[RotationEffectObligationRankingResult, ...],
        *,
        expected: set[str],
    ) -> None:
        seen: set[str] = set()
        ranks: list[int] = []
        for item in ranking:
            candidate_id = str(item.candidate_id or "").strip()
            if not candidate_id:
                raise ValueError("support cadence ranking candidate_id must be non-empty")
            key = candidate_id.casefold()
            if key in seen:
                raise ValueError(
                    f"duplicate support cadence ranking candidate_id: {candidate_id!r}"
                )
            seen.add(key)
            ranks.append(int(item.rank))

        if seen != expected:
            missing = sorted(expected - seen)
            unexpected = sorted(seen - expected)
            details: list[str] = []
            if missing:
                details.append("missing: " + ", ".join(missing))
            if unexpected:
                details.append("unexpected: " + ", ".join(unexpected))
            raise ValueError(
                "support cadence ranking must exactly match evaluated candidates"
                + (" (" + "; ".join(details) + ")" if details else "")
            )

        expected_ranks = list(range(1, len(ranking) + 1))
        if ranks != expected_ranks:
            raise ValueError(
                "support cadence ranking must be supplied in contiguous rank order starting at 1"
            )


__all__ = [
    "RotationSupportCadenceRecommendationCandidate",
    "RotationSupportCadenceRecommendationResult",
    "RotationSupportCadenceRecommendationService",
]
