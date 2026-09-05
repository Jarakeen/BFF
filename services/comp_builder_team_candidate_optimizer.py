from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from services.comp_builder_build_candidates import CompBuildCandidate
from services.comp_builder_composition_style import (
    CompCompositionStyle,
    composition_style_policy,
)


@dataclass(frozen=True)
class CompTeamCandidatePool:
    slot_name: str
    candidates: tuple[CompBuildCandidate, ...]
    required_provider_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompTeamCandidateAssignment:
    slot_name: str
    candidate: CompBuildCandidate | None


@dataclass(frozen=True)
class CompTeamCandidateOptimizationResult:
    assignments: tuple[CompTeamCandidateAssignment, ...]
    provider_blocked_slots: tuple[str, ...] = ()
    uncovered_team_provider_ids: tuple[str, ...] = ()

    @property
    def applied_count(self) -> int:
        return sum(1 for assignment in self.assignments if assignment.candidate is not None)

    @property
    def unresolved_slots(self) -> tuple[str, ...]:
        return tuple(
            assignment.slot_name
            for assignment in self.assignments
            if assignment.candidate is None
        )


def _clean_provider_ids(values: tuple[str, ...]) -> frozenset[str]:
    return frozenset(
        text
        for value in values
        if (text := str(value or "").strip())
    )


def _saved_player_key(candidate: CompBuildCandidate) -> str:
    if candidate.source_kind != "saved_build":
        return ""
    return str(candidate.source_name or "").strip().casefold()


def _option_value(
    candidate: CompBuildCandidate | None,
    *,
    novelty_by_candidate: dict[str, float],
) -> tuple[int, int, float, float]:
    if candidate is None:
        return (0, 0, 0.0, 0.0)
    return (
        1,
        1 if candidate.source_kind == "saved_build" else 0,
        float(candidate.score),
        float(novelty_by_candidate.get(candidate.candidate_id, 0.0)),
    )


def _style_value(
    *,
    style: CompCompositionStyle,
    filled: int,
    coverage_count: int,
    saved_build_count: int,
    relevance: float,
    novelty: float,
    all_team_required_covered: int,
) -> tuple[float, ...]:
    policy = composition_style_policy(style)

    # Hard raid validity always wins. Style only influences already-legal teams.
    hard_prefix = (
        float(all_team_required_covered),
        float(filled),
        float(coverage_count),
    )

    if policy.style is CompCompositionStyle.PROVEN:
        return (*hard_prefix, float(saved_build_count), float(relevance), float(novelty))
    if policy.style is CompCompositionStyle.PERFORMANCE:
        return (*hard_prefix, float(relevance), float(saved_build_count), float(novelty))

    discovery = (
        float(novelty) * float(policy.novelty_weight)
        + float(relevance) * float(policy.relevance_weight)
    )
    return (*hard_prefix, discovery, float(relevance), float(saved_build_count))


def _better(
    left: tuple[tuple[float, ...], tuple[str, ...]],
    right: tuple[tuple[float, ...], tuple[str, ...]],
) -> bool:
    if left[0] != right[0]:
        return left[0] > right[0]
    return left[1] < right[1]


def optimize_comp_team_candidates(
    *,
    pools: tuple[CompTeamCandidatePool, ...],
    already_used_saved_players: tuple[str, ...] = (),
    provider_ids_by_candidate: dict[str, tuple[str, ...]] | None = None,
    required_team_provider_ids: tuple[str, ...] = (),
    already_covered_team_provider_ids: tuple[str, ...] = (),
    composition_style: CompCompositionStyle | str = CompCompositionStyle.PROVEN,
    novelty_by_candidate: dict[str, float] | None = None,
) -> CompTeamCandidateOptimizationResult:
    """Choose a coherent team assignment from per-chair Comp Maker candidates.

    Saved players are consumable once. Reference templates are reusable recruitment
    evidence. Chair-local provider requirements remain hard eligibility constraints.

    Raid-wide provider requirements are also hard team validity. Composition style
    can change which *legal* team wins, but it cannot trade away chair fill, required
    provider coverage, or other candidate gates established before this solver runs.

    ``novelty_by_candidate`` is deliberately external evidence. Experimental modes do
    not invent rarity from source names or labels; a candidate receives no novelty
    credit unless an evidence-producing layer supplies it.
    """

    style = composition_style_policy(composition_style).style
    novelty_by_candidate = {
        str(candidate_id): float(value)
        for candidate_id, value in (novelty_by_candidate or {}).items()
    }
    provider_ids_by_candidate = provider_ids_by_candidate or {}
    normalized_provider_ids = {
        str(candidate_id): _clean_provider_ids(tuple(values))
        for candidate_id, values in provider_ids_by_candidate.items()
    }
    normalized_used = tuple(
        sorted(
            {
                str(value or "").strip().casefold()
                for value in already_used_saved_players
                if str(value or "").strip()
            }
        )
    )
    required_team = _clean_provider_ids(required_team_provider_ids)
    initial_covered = _clean_provider_ids(already_covered_team_provider_ids) & required_team

    provider_blocked_slots: list[str] = []
    eligible_by_slot: list[tuple[CompBuildCandidate, ...]] = []
    for pool in pools:
        required = _clean_provider_ids(pool.required_provider_ids)
        if not required:
            eligible_by_slot.append(pool.candidates)
            continue
        eligible = tuple(
            candidate
            for candidate in pool.candidates
            if required.issubset(
                normalized_provider_ids.get(candidate.candidate_id, frozenset())
            )
        )
        eligible_by_slot.append(eligible)
        if pool.candidates and not eligible:
            provider_blocked_slots.append(pool.slot_name)

    @lru_cache(maxsize=None)
    def solve(index: int, used: tuple[str, ...], covered: tuple[str, ...]):
        covered_set = set(covered)
        if index >= len(pools):
            coverage_count = len(required_team & covered_set)
            all_team_required_covered = int(required_team.issubset(covered_set))
            value = _style_value(
                style=style,
                filled=0,
                coverage_count=coverage_count,
                saved_build_count=0,
                relevance=0.0,
                novelty=0.0,
                all_team_required_covered=all_team_required_covered,
            )
            return (
                value,
                (),
                (),
                tuple(sorted(covered_set)),
                0,
                0,
                0.0,
                0.0,
            )

        used_set = set(used)
        options: tuple[CompBuildCandidate | None, ...] = (
            *eligible_by_slot[index],
            None,
        )
        best = None

        for candidate in options:
            player_key = _saved_player_key(candidate) if candidate is not None else ""
            if player_key and player_key in used_set:
                continue

            next_used = tuple(sorted((*used_set, player_key))) if player_key else used
            candidate_providers = (
                normalized_provider_ids.get(candidate.candidate_id, frozenset())
                if candidate is not None
                else frozenset()
            )
            next_covered = tuple(sorted(covered_set | (candidate_providers & required_team)))
            (
                _tail_value,
                tail_ids,
                tail_candidates,
                tail_covered,
                tail_filled,
                tail_saved,
                tail_relevance,
                tail_novelty,
            ) = solve(index + 1, next_used, next_covered)
            own_filled, own_saved, own_relevance, own_novelty = _option_value(
                candidate,
                novelty_by_candidate=novelty_by_candidate,
            )
            filled = own_filled + tail_filled
            saved = own_saved + tail_saved
            relevance = own_relevance + tail_relevance
            novelty = own_novelty + tail_novelty
            covered_final = set(tail_covered)
            coverage_count = len(required_team & covered_final)
            all_team_required_covered = int(required_team.issubset(covered_final))
            total_value = _style_value(
                style=style,
                filled=filled,
                coverage_count=coverage_count,
                saved_build_count=saved,
                relevance=relevance,
                novelty=novelty,
                all_team_required_covered=all_team_required_covered,
            )
            candidate_id = candidate.candidate_id if candidate is not None else "~unresolved"
            ids = (candidate_id.casefold(), *tail_ids)
            proposal = (
                total_value,
                ids,
                (candidate, *tail_candidates),
                tail_covered,
                filled,
                saved,
                relevance,
                novelty,
            )
            if best is None or _better(
                (proposal[0], proposal[1]),
                (best[0], best[1]),
            ):
                best = proposal

        assert best is not None
        return best

    _value, _ids, selected, covered, *_metrics = solve(
        0,
        normalized_used,
        tuple(sorted(initial_covered)),
    )
    covered_set = frozenset(covered)
    return CompTeamCandidateOptimizationResult(
        assignments=tuple(
            CompTeamCandidateAssignment(slot_name=pool.slot_name, candidate=candidate)
            for pool, candidate in zip(pools, selected, strict=True)
        ),
        provider_blocked_slots=tuple(provider_blocked_slots),
        uncovered_team_provider_ids=tuple(sorted(required_team - covered_set)),
    )
