from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from minmax.character_build.character_build import CharacterBuild
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingResult,
    RotationCandidateRankingService,
    RotationCandidateTier,
)
from services.rotation_candidate_scorecard_service import (
    RotationCandidateScorecard,
    RotationCandidateScorecardService,
)
from services.rotation_heavy_attack_restoration_evidence_service import (
    RotationHeavyAttackCompletionEvidence,
)
from services.rotation_heavy_sustain_projection_service import (
    RotationHeavySustainProjection,
    RotationHeavySustainProjectionService,
)
from services.rotation_sustain_service import RotationSustainProjection


@dataclass(frozen=True)
class RotationCandidateHeavySustainInput:
    """One generated candidate plus explicit heavy-completion evidence."""

    candidate_id: str
    plan: RotationPlan
    completion_evidence: tuple[RotationHeavyAttackCompletionEvidence, ...] = ()

    def __post_init__(self) -> None:
        value = str(self.candidate_id or "").strip()
        if not value:
            raise ValueError("rotation heavy-sustain candidate_id must be non-empty")
        object.__setattr__(self, "candidate_id", value)


@dataclass(frozen=True)
class RotationCandidateHeavySustainResult:
    """Candidate state after post-heavy sustain scoring and hard evidence gating."""

    candidate_id: str
    plan: RotationPlan
    heavy_projection: RotationHeavySustainProjection
    scorecard: RotationCandidateScorecard | None
    tier: RotationCandidateTier
    rank: int
    reasons: tuple[str, ...]


class RotationCandidateHeavySustainRankingService:
    """Replay verified heavy restores before scorecard/ranking obligations run.

    Resource shortfall and reserve requirements are hard obligations in the generic
    scorecard. This service therefore projects each candidate's verified heavy
    restoration first and hands the resulting post-heavy sustain timeline to the
    scorecard. Missing/ambiguous heavy evidence is a hard failure here; it never
    becomes a zero-value restore or a merely cosmetic unresolved note.

    `baseline_sustain` is caller supplied intentionally. If the baseline plan has
    verified heavy attacks, the caller must supply a baseline sustain projection that
    already contains those restores so consequence comparisons remain symmetric.
    """

    def __init__(
        self,
        *,
        heavy_service: RotationHeavySustainProjectionService | None = None,
        scorecard_service: RotationCandidateScorecardService | None = None,
        ranking_service: RotationCandidateRankingService | None = None,
    ) -> None:
        self.heavy_service = heavy_service or RotationHeavySustainProjectionService()
        self.scorecard_service = scorecard_service or RotationCandidateScorecardService()
        self.ranking_service = ranking_service or RotationCandidateRankingService()

    def evaluate_and_rank(
        self,
        *,
        character_build: CharacterBuild,
        sustain_build: PlayerBuild,
        resource: ResourceType,
        initial_bar: str,
        baseline_plan: RotationPlan,
        baseline_sustain: RotationSustainProjection,
        candidates: tuple[RotationCandidateHeavySustainInput, ...],
        scorecard_kwargs: dict[str, Any] | None = None,
    ) -> tuple[RotationCandidateHeavySustainResult, ...]:
        if not candidates:
            return ()

        seen: set[str] = set()
        for candidate in candidates:
            key = candidate.candidate_id.casefold()
            if key in seen:
                raise ValueError(
                    f"duplicate rotation heavy-sustain candidate_id: {candidate.candidate_id!r}"
                )
            seen.add(key)

        kwargs = dict(scorecard_kwargs or {})
        forbidden = {
            "baseline_plan",
            "candidate_plan",
            "baseline_sustain",
            "candidate_sustain",
        }
        overlap = sorted(forbidden.intersection(kwargs))
        if overlap:
            raise ValueError(
                "heavy-sustain scorecard_kwargs cannot override managed argument(s): "
                + ", ".join(overlap)
            )

        resolved: dict[str, tuple[RotationCandidateHeavySustainInput, RotationHeavySustainProjection, RotationCandidateScorecard]] = {}
        unresolved: list[tuple[RotationCandidateHeavySustainInput, RotationHeavySustainProjection]] = []

        for candidate in candidates:
            key = candidate.candidate_id.casefold()
            projection = self.heavy_service.project(
                character_build=character_build,
                sustain_build=sustain_build,
                plan=candidate.plan,
                resource=resource,
                initial_bar=initial_bar,
                completion_evidence=tuple(candidate.completion_evidence),
            )
            candidate_sustain = projection.sustain_projection
            if candidate_sustain is None or projection.unresolved:
                unresolved.append((candidate, projection))
                continue

            scorecard = self.scorecard_service.compare(
                baseline_plan=baseline_plan,
                candidate_plan=candidate.plan,
                baseline_sustain=baseline_sustain,
                candidate_sustain=candidate_sustain,
                **kwargs,
            )
            resolved[key] = (candidate, projection, scorecard)

        ranked = self.ranking_service.rank(
            tuple(
                RotationCandidateRankingInput(
                    candidate_id=item[0].candidate_id,
                    scorecard=item[2],
                )
                for item in resolved.values()
            )
        )
        if {item.candidate_id.casefold() for item in ranked} != set(resolved):
            raise ValueError("rotation ranking returned a different resolved candidate set")

        staged: list[tuple[tuple[object, ...], RotationCandidateHeavySustainResult]] = []
        for ranked_item in ranked:
            candidate, projection, scorecard = resolved[ranked_item.candidate_id.casefold()]
            result = RotationCandidateHeavySustainResult(
                candidate_id=candidate.candidate_id,
                plan=candidate.plan,
                heavy_projection=projection,
                scorecard=scorecard,
                tier=ranked_item.tier,
                rank=0,
                reasons=tuple(ranked_item.reasons),
            )
            staged.append(
                (
                    (
                        0 if ranked_item.tier is RotationCandidateTier.ELIGIBLE else 1,
                        0,
                        ranked_item.rank,
                        candidate.candidate_id.casefold(),
                    ),
                    result,
                )
            )

        for candidate, projection in unresolved:
            reasons = tuple(
                f"heavy sustain projection unresolved: {detail}"
                for detail in projection.unresolved
            ) or ("heavy sustain projection unresolved",)
            staged.append(
                (
                    (1, 1, len(projection.unresolved), candidate.candidate_id.casefold()),
                    RotationCandidateHeavySustainResult(
                        candidate_id=candidate.candidate_id,
                        plan=candidate.plan,
                        heavy_projection=projection,
                        scorecard=None,
                        tier=RotationCandidateTier.INELIGIBLE,
                        rank=0,
                        reasons=reasons,
                    ),
                )
            )

        staged.sort(key=lambda item: item[0])
        return tuple(
            RotationCandidateHeavySustainResult(
                candidate_id=result.candidate_id,
                plan=result.plan,
                heavy_projection=result.heavy_projection,
                scorecard=result.scorecard,
                tier=result.tier,
                rank=index + 1,
                reasons=result.reasons,
            )
            for index, (_key, result) in enumerate(staged)
        )


__all__ = [
    "RotationCandidateHeavySustainInput",
    "RotationCandidateHeavySustainRankingService",
    "RotationCandidateHeavySustainResult",
]
