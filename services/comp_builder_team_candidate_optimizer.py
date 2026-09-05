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
    left: tuple[tuple[int, int, float], tuple[str, ...]],
    right: tuple[tuple[int, int, float], tuple[str, ...]],
) -> bool:
    if left[0] != right[0]:
        return left[0] > right[0]
    return left[1] < right[1]


def optimize_comp_team_candidates(
    *,
    pools: tuple[CompTeamCandidatePool, ...],
    already_used_saved_players: tuple[str, ...] = (),
    provider_ids_by_candidate: dict[str, tuple[str, ...]] | None = None,
) -> CompTeamCandidateOptimizationResult:
    """Choose a coherent team assignment from per-chair Comp Maker candidates.

    Saved players are consumable once. Reference templates are reusable recruitment
    evidence. When a chair carries canonically mapped provider requirements, candidates
    that cannot prove every required provider identity are ineligible. Unsupported or
    unresolved provider evidence therefore cannot win through a relevance score.
    """

    provider_ids_by_candidate = provider_ids_by_candidate or {}
    normalized_provider_ids = {
        str(candidate_id): frozenset(
            str(value or "").strip()
            for value in values
            if str(value or "").strip()
        )
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

    provider_blocked_slots: list[str] = []
    eligible_by_slot: list[tuple[CompBuildCandidate, ...]] = []
    for pool in pools:
        required = frozenset(
            str(value or "").strip()
            for value in pool.required_provider_ids
            if str(value or "").strip()
        )
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
    def solve(index: int, used: tuple[str, ...]):
        if index >= len(pools):
            return ((0, 0, 0.0), (), ())

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
            tail_value, tail_ids, tail_candidates = solve(index + 1, next_used)
            own = _option_value(candidate)
            total_value = (
                own[0] + tail_value[0],
                own[1] + tail_value[1],
                own[2] + tail_value[2],
            )
            candidate_id = candidate.candidate_id if candidate is not None else "~unresolved"
            ids = (candidate_id.casefold(), *tail_ids)
            proposal = (total_value, ids, (candidate, *tail_candidates))
            if best is None or _better(
                (proposal[0], proposal[1]),
                (best[0], best[1]),
            ):
                best = proposal

        assert best is not None
        return best

    _value, _ids, selected = solve(0, normalized_used)
    return CompTeamCandidateOptimizationResult(
        assignments=tuple(
            CompTeamCandidateAssignment(slot_name=pool.slot_name, candidate=candidate)
            for pool, candidate in zip(pools, selected, strict=True)
        ),
        provider_blocked_slots=tuple(provider_blocked_slots),
    )
