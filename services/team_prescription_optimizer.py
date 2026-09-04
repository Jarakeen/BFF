from __future__ import annotations

from dataclasses import dataclass

from .team_prescription import PrescribedRoster
from .team_prescription_candidate_application import (
    apply_ranked_candidate_to_prescribed_roster,
)
from .team_prescription_candidate_ranking import (
    PrescribedSlotCandidateEvidence,
    PrescribedSlotCandidateRanking,
    rank_prescribed_slot_candidates,
)


@dataclass(frozen=True)
class PrescribedSlotOptimization:
    slot_name: str
    ranking: PrescribedSlotCandidateRanking | None
    applied: bool
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class TeamPrescriptionOptimizationResult:
    original_roster: PrescribedRoster
    final_roster: PrescribedRoster
    slots: tuple[PrescribedSlotOptimization, ...]

    @property
    def applied_count(self) -> int:
        return sum(1 for slot in self.slots if slot.applied)

    @property
    def unresolved(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                message
                for slot in self.slots
                for message in slot.unresolved
                if str(message).strip()
            )
        )


def optimize_prescribed_roster_candidates(
    *,
    roster: PrescribedRoster,
    candidate_pools: dict[str, tuple[PrescribedSlotCandidateEvidence, ...]],
    provider_requirements_by_slot: dict[str, tuple[str, ...]] | None = None,
) -> TeamPrescriptionOptimizationResult:
    """Rank and apply evidence-backed candidate pools to every open roster slot.

    This is deliberately an orchestration layer. Candidate generation and Phase 12
    evaluation stay authoritative in their existing services. A missing pool is
    reported as unresolved rather than converted into a fabricated recommendation.
    Anchored saved players are never replaced here.
    """

    provider_requirements_by_slot = provider_requirements_by_slot or {}
    normalized_pools = {
        str(slot_name).strip().casefold(): tuple(candidates)
        for slot_name, candidates in candidate_pools.items()
        if str(slot_name).strip()
    }
    normalized_requirements = {
        str(slot_name).strip().casefold(): tuple(requirements)
        for slot_name, requirements in provider_requirements_by_slot.items()
        if str(slot_name).strip()
    }

    current = roster
    decisions: list[PrescribedSlotOptimization] = []

    for assignment in roster.assignments:
        if assignment.player_name is not None:
            decisions.append(
                PrescribedSlotOptimization(
                    slot_name=assignment.slot_name,
                    ranking=None,
                    applied=False,
                )
            )
            continue

        slot_key = assignment.slot_name.casefold()
        candidates = normalized_pools.get(slot_key, ())
        if not candidates:
            unresolved = (
                f"{assignment.slot_name}: no evaluated candidate pool is available; "
                "prescription remains unresolved",
            )
            decisions.append(
                PrescribedSlotOptimization(
                    slot_name=assignment.slot_name,
                    ranking=None,
                    applied=False,
                    unresolved=unresolved,
                )
            )
            continue

        ranking = rank_prescribed_slot_candidates(
            slot_name=assignment.slot_name,
            required_provider_requirement_ids=normalized_requirements.get(slot_key, ()),
            candidates=candidates,
        )
        before = current
        current = apply_ranked_candidate_to_prescribed_roster(
            roster=current,
            ranking=ranking,
        )
        applied = ranking.recommended is not None and current != before
        unresolved = ranking.unresolved
        if ranking.recommended is None and not unresolved:
            unresolved = (
                f"{assignment.slot_name}: no eligible Phase 12 candidate satisfied "
                "the role and hard provider constraints",
            )
        decisions.append(
            PrescribedSlotOptimization(
                slot_name=assignment.slot_name,
                ranking=ranking,
                applied=applied,
                unresolved=unresolved,
            )
        )

    return TeamPrescriptionOptimizationResult(
        original_roster=roster,
        final_roster=current,
        slots=tuple(decisions),
    )
