from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from services.comp_builder_build_candidates import CompBuildCandidate
from services.team_role_autofill import normalize_team_role


_MIN_ROLE_SAMPLE = 3


@dataclass(frozen=True)
class CompStrategyEvidence:
    candidate_id: str
    strategy_score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CompStrategyEvidenceResult:
    evidence: tuple[CompStrategyEvidence, ...]

    @property
    def score_by_candidate(self) -> dict[str, float]:
        return {row.candidate_id: row.strategy_score for row in self.evidence}


def evaluate_provider_redistribution_strategy(
    candidates: Iterable[CompBuildCandidate],
    *,
    provider_ids_by_candidate: dict[str, tuple[str, ...]],
) -> CompStrategyEvidenceResult:
    """Score unusual provider ownership using canonical candidate evidence only.

    This is structural strategy evidence, not observed ESO Logs frequency. A provider
    scores as interesting when it is canonically provable on relatively few candidates
    for that candidate's role. Unknown provider evidence receives no credit.
    """

    rows = tuple(candidates)
    role_totals: dict[str, int] = {}
    provider_role_counts: dict[tuple[str, str], int] = {}

    for candidate in rows:
        role = normalize_team_role(candidate.role)
        if role is None:
            continue
        role_totals[role] = role_totals.get(role, 0) + 1
        for provider_id in set(provider_ids_by_candidate.get(candidate.candidate_id, ())):
            key = (role, str(provider_id))
            provider_role_counts[key] = provider_role_counts.get(key, 0) + 1

    evidence: list[CompStrategyEvidence] = []
    for candidate in rows:
        role = normalize_team_role(candidate.role)
        total = role_totals.get(role or "", 0)
        providers = tuple(dict.fromkeys(provider_ids_by_candidate.get(candidate.candidate_id, ())))
        reasons: list[str] = []

        if role is None or total < _MIN_ROLE_SAMPLE:
            evidence.append(
                CompStrategyEvidence(
                    candidate_id=candidate.candidate_id,
                    strategy_score=0.0,
                    reasons=(f"insufficient same-role candidate sample for strategy ({total}/{_MIN_ROLE_SAMPLE})",),
                )
            )
            continue
        if not providers:
            evidence.append(
                CompStrategyEvidence(
                    candidate_id=candidate.candidate_id,
                    strategy_score=0.0,
                    reasons=("no canonically proven provider ownership available for redistribution scoring",),
                )
            )
            continue

        rarities: list[float] = []
        for provider_id in providers:
            count = provider_role_counts.get((role, provider_id), 0)
            rarity = 1.0 - (count / float(total))
            rarities.append(rarity)
            reasons.append(
                f"{provider_id} is provable on {count}/{total} eligible {role} candidate(s)"
            )

        score = max(0.0, min(100.0, 100.0 * (sum(rarities) / len(rarities))))
        evidence.append(
            CompStrategyEvidence(
                candidate_id=candidate.candidate_id,
                strategy_score=score,
                reasons=tuple(reasons),
            )
        )

    return CompStrategyEvidenceResult(tuple(evidence))
