from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from services.comp_builder_build_candidates import CompBuildCandidate


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


def _option_value(candidate: CompBuildCandidate | None) -> tuple[int, int, float]:
    if candidate is None:
        return (0, 0, 0.0)
    return (
        1,
        1 if candidate.source_kind == "saved_build" else 0,
        float(candidate.score),
    )


def _better(
    left: tuple[tuple[int, int, int, int, float], tuple[str, ...]],
    right: tuple[tuple[int, int, int, int, float], tuple[str, ...]],
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
) -> CompTeamCandidateOptimizationResult:
    """Choose a coherent team assignment from per-chair Comp Maker candidates.

    Saved players are consumable once. Reference templates are reusable recruitment
    evidence. Chair-local provider requirements remain hard eligibility constraints.

    Raid-wide provider requirements are a separate concern: when a full-coverage
    assignment is possible, it outranks an otherwise stronger relevance assignment.
    If complete raid coverage is impossible, the optimizer preserves maximum chair
    fill first and then prefers the assignment covering the most remaining raid-wide
    providers. This keeps impossible coverage explicit instead of sacrificing most of
    the roster merely to satisfy one isolated effect.
    """

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
            return (
                (all_team_required_covered, 0, coverage_count, 0, 0.0),
                (),
                (),
                tuple(sorted(covered_set)),
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
            tail_value, tail_ids, tail_candidates, tail_covered = solve(
                index + 1,
                next_used,
                next_covered,
            )
            own = _option_value(candidate)
            total_value = (
                tail_value[0],
                own[0] + tail_value[1],
                tail_value[2],
                own[1] + tail_value[3],
                own[2] + tail_value[4],
            )
            candidate_id = candidate.candidate_id if candidate is not None else "~unresolved"
            ids = (candidate_id.casefold(), *tail_ids)
            proposal = (total_value, ids, (candidate, *tail_candidates), tail_covered)
            if best is None or _better(
                (proposal[0], proposal[1]),
                (best[0], best[1]),
            ):
                best = proposal

        assert best is not None
        return best

    _value, _ids, selected, covered = solve(
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
