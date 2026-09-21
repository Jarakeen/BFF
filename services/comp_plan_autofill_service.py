from __future__ import annotations

"""Apply whole-team Comp candidate optimization to canonical CompPlanState.

This service owns state mutation for Auto-Fill Builds. Candidate discovery and provider
proof remain upstream services; this layer decides which unlocked/open Comp fields may
be populated from the optimizer result.
"""

from dataclasses import dataclass

from models.comp_plan_state import CompChairState, CompPlanState
from services.comp_builder_build_candidates import CompBuildCandidate
from services.comp_builder_composition_style import CompCompositionStyle
from services.comp_builder_team_candidate_optimizer import (
    CompTeamCandidateOptimizationResult,
    CompTeamCandidatePool,
    optimize_comp_team_candidates,
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _seat_key(value: object) -> str:
    text = _clean(value).casefold().replace("_", " ").replace("-", " ")
    return "-".join(text.split())


def _same_identity(left: object, right: object) -> bool:
    a = _clean(left).casefold()
    b = _clean(right).casefold()
    return bool(a and b and a == b)


@dataclass(frozen=True)
class CompAutoFillChange:
    seat_id: str
    candidate_id: str
    candidate_name: str
    changed_fields: tuple[str, ...]


@dataclass(frozen=True)
class CompAutoFillResult:
    state: CompPlanState
    optimization: CompTeamCandidateOptimizationResult
    changes: tuple[CompAutoFillChange, ...]
    skipped_existing: tuple[str, ...]

    @property
    def applied_count(self) -> int:
        return len(self.changes)


class CompPlanAutoFillService:
    """Fill unresolved Comp decisions while preserving existing and locked choices."""

    @staticmethod
    def chair_is_open_for_build_autofill(chair: CompChairState) -> bool:
        if chair.is_locked("build") or chair.is_locked("gear"):
            return False
        if chair.selected_build_id or chair.selected_build_name:
            return False
        if chair.planned_gear_sets:
            return False
        return True

    @staticmethod
    def _candidate_changes(
        chair: CompChairState,
        candidate: CompBuildCandidate,
        *,
        provider_required: bool = False,
    ) -> dict[str, object]:
        changes: dict[str, object] = {}

        # Saved builds are player-owned evidence. A saved build belonging to another
        # canonical player/character is not a reusable template and may not donate
        # class, gear, Mundus, or selected-build state to this chair.
        can_bind_saved_build = candidate.source_kind == "saved_build" and (
            (
                bool(chair.player_id and candidate.saved_player_id)
                and _same_identity(chair.player_id, candidate.saved_player_id)
            )
            or (
                bool(chair.character_id and candidate.saved_character_id)
                and _same_identity(chair.character_id, candidate.saved_character_id)
            )
            or (
                not chair.player_id
                and not chair.character_id
                and (
                    _same_identity(chair.player_name, candidate.source_name)
                    or _same_identity(chair.character_name, candidate.source_name)
                )
            )
        )
        open_recruit = (
            candidate.source_kind == "saved_build"
            and not can_bind_saved_build
            and not _clean(chair.player_id)
            and not _clean(chair.character_id)
            and not _clean(chair.player_name)
            and not _clean(chair.character_name)
        )
        if candidate.source_kind == "saved_build" and not can_bind_saved_build and not open_recruit:
            return {}

        if (
            not chair.is_locked("class")
            and not _clean(chair.eso_class)
            and _clean(candidate.eso_class)
        ):
            changes["eso_class"] = _clean(candidate.eso_class)

        if (
            can_bind_saved_build
            and not chair.is_locked("build")
            and not chair.selected_build_id
            and not chair.selected_build_name
        ):
            changes["selected_build_id"] = candidate.saved_build_id or None
            changes["selected_build_name"] = candidate.name

        if (
            not chair.is_locked("gear")
            and not chair.planned_gear_sets
            and tuple(candidate.gear_sets)
        ):
            changes["planned_gear_sets"] = tuple(candidate.gear_sets)

        if (
            not chair.is_locked("mundus")
            and not _clean(chair.planned_mundus)
            and _clean(candidate.mundus)
        ):
            changes["planned_mundus"] = _clean(candidate.mundus)

        if (
            provider_required
            and not chair.is_locked("skills")
            and not chair.planned_skills
            and tuple(candidate.skills)
        ):
            changes["planned_skills"] = tuple(candidate.skills)

        # Provenance is attached only when the candidate actually fills a planning
        # field. Thin evidence rows cannot masquerade as completed Auto-Fill work.
        if changes:
            changes.update(
                build_source_kind=candidate.source_kind,
                build_source_name=candidate.source_name,
                build_source_url=candidate.source_url,
                candidate_id=candidate.candidate_id,
            )

        # Skills are adopted only when this chair has an explicit assigned provider
        # responsibility and the selected candidate carries known skill evidence.
        # Generic roster fill continues to leave skills untouched.
        return changes

    def apply(
        self,
        *,
        state: CompPlanState,
        pools: tuple[CompTeamCandidatePool, ...],
        already_used_saved_players: tuple[str, ...] = (),
        provider_ids_by_candidate: dict[str, tuple[str, ...]] | None = None,
        required_team_provider_ids: tuple[str, ...] = (),
        already_covered_team_provider_ids: tuple[str, ...] = (),
        composition_style: CompCompositionStyle | str = CompCompositionStyle.PROVEN,
        novelty_by_candidate: dict[str, float] | None = None,
    ) -> CompAutoFillResult:
        if not isinstance(state, CompPlanState):
            raise TypeError("Comp Auto-Fill requires CompPlanState")

        open_pools: list[CompTeamCandidatePool] = []
        skipped: list[str] = []
        for pool in pools:
            wanted = _seat_key(pool.slot_name)
            chair = next(
                (
                    item
                    for item in state.chairs
                    if _seat_key(item.seat_id) == wanted
                ),
                None,
            )
            if chair is None:
                continue
            if not self.chair_is_open_for_build_autofill(chair):
                skipped.append(chair.seat_id)
                continue
            open_pools.append(pool)

        optimization = optimize_comp_team_candidates(
            pools=tuple(open_pools),
            already_used_saved_players=already_used_saved_players,
            provider_ids_by_candidate=provider_ids_by_candidate,
            required_team_provider_ids=required_team_provider_ids,
            already_covered_team_provider_ids=already_covered_team_provider_ids,
            composition_style=composition_style,
            novelty_by_candidate=novelty_by_candidate,
        )

        required_by_slot = {
            _seat_key(pool.slot_name): bool(pool.required_provider_ids)
            for pool in open_pools
        }

        updated = state
        changes: list[CompAutoFillChange] = []
        for assignment in optimization.assignments:
            candidate = assignment.candidate
            if candidate is None:
                continue
            wanted = _seat_key(assignment.slot_name)
            chair = next(
                (
                    item
                    for item in updated.chairs
                    if _seat_key(item.seat_id) == wanted
                ),
                None,
            )
            if chair is None:
                continue
            field_changes = self._candidate_changes(
                chair,
                candidate,
                provider_required=required_by_slot.get(wanted, False),
            )
            if not field_changes:
                continue
            updated = updated.with_chair(chair.with_changes(**field_changes))
            changes.append(
                CompAutoFillChange(
                    seat_id=chair.seat_id,
                    candidate_id=candidate.candidate_id,
                    candidate_name=candidate.name,
                    changed_fields=tuple(field_changes),
                )
            )

        return CompAutoFillResult(
            state=updated,
            optimization=optimization,
            changes=tuple(changes),
            skipped_existing=tuple(skipped),
        )


__all__ = [
    "CompAutoFillChange",
    "CompAutoFillResult",
    "CompPlanAutoFillService",
]
