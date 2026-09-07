from __future__ import annotations

from dataclasses import dataclass

from .named_buff_resolution_service import NamedBuffContribution
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


def _saved_player_name(evidence: PrescribedSlotCandidateEvidence) -> str | None:
    if evidence.open_slot is None:
        return None
    return evidence.open_slot.candidate.player_name


def optimize_prescribed_roster_candidates(
    *,
    roster: PrescribedRoster,
    candidate_pools: dict[str, tuple[PrescribedSlotCandidateEvidence, ...]],
    provider_requirements_by_slot: dict[str, tuple[str, ...]] | None = None,
    provider_required_recipients_by_slot: dict[str, dict[str, int]] | None = None,
    existing_team_effects: tuple[NamedBuffContribution, ...] = (),
) -> TeamPrescriptionOptimizationResult:
    """Rank and apply evidence-backed candidate pools to genuinely open chairs.

    Anchored saved players, complete prescribed build snapshots, and partial template
    recommendations already selected by an earlier-priority source are preserved.
    User ingredient-only constraints remain open and are enforced by candidate
    generation before this optimizer receives the pool.

    ``existing_team_effects`` describes reviewed named effects already supplied by
    anchored roster members, potion plans, sets, or other team context. After an open
    slot is filled, the selected candidate's reviewed provider effects are carried
    forward so later slots receive credit only for effects still missing from the
    evolving team. Provider effects are a tie-break signal only; they are never added
    numerically to unlike canonical objective scores.

    ``provider_required_recipients_by_slot`` adds a coverage-capacity requirement to
    selected provider IDs. A candidate that owns the provider ID but cannot prove it
    reaches the requested number of recipients is rejected. Slots/providers omitted
    from this mapping retain the legacy identity-only requirement behavior.
    """

    provider_requirements_by_slot = provider_requirements_by_slot or {}
    provider_required_recipients_by_slot = provider_required_recipients_by_slot or {}
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
    normalized_recipient_requirements = {
        str(slot_name).strip().casefold(): dict(requirements)
        for slot_name, requirements in provider_required_recipients_by_slot.items()
        if str(slot_name).strip()
    }

    current = roster
    decisions: list[PrescribedSlotOptimization] = []
    team_effects = list(existing_team_effects)
    used_saved_players = {
        assignment.player_name.casefold()
        for assignment in roster.assignments
        if assignment.player_name
    }

    for assignment in roster.assignments:
        if not assignment.is_open_for_candidate:
            decisions.append(
                PrescribedSlotOptimization(
                    slot_name=assignment.slot_name,
                    ranking=None,
                    applied=False,
                )
            )
            continue

        slot_key = assignment.slot_name.casefold()
        raw_candidates = normalized_pools.get(slot_key, ())
        candidates = tuple(
            evidence
            for evidence in raw_candidates
            if not (
                (player_name := _saved_player_name(evidence))
                and player_name.casefold() in used_saved_players
            )
        )
        if not candidates:
            if raw_candidates:
                unresolved = (
                    f"{assignment.slot_name}: every evaluated saved-player candidate "
                    "is already assigned to another roster slot",
                )
            else:
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
            existing_team_effects=tuple(team_effects),
            provider_required_recipients_by_id=normalized_recipient_requirements.get(
                slot_key,
                {},
            ),
        )
        before = current
        current = apply_ranked_candidate_to_prescribed_roster(
            roster=current,
            ranking=ranking,
        )
        applied = ranking.recommended is not None and current != before
        if applied and ranking.recommended is not None:
            player_name = _saved_player_name(ranking.recommended)
            if player_name:
                used_saved_players.add(player_name.casefold())
            team_effects.extend(ranking.recommended.provider_effects)

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
