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
    ) -> dict[str, object]:
        changes: dict[str, object] = {}

        if (
            not chair.is_locked("class")
            and not _clean(chair.eso_class)
            and _clean(candidate.eso_class)
        ):
            changes["eso_class"] = _clean(candidate.eso_class)

        # A saved build may be bound as the chair's selected build only when its owner
        # matches the already-selected player. Recruit/open chairs may still consume
        # its gear/class as planning evidence without fabricating that player identity.
        can_bind_saved_build = (
            candidate.source_kind == "saved_build"
            and _same_identity(chair.player_name, candidate.source_name)
        )
        if (
            can_bind_saved_build
            and not chair.is_locked("build")
            and not chair.selected_build_id
            and not chair.selected_build_name
        ):
            changes.update(
                selected_build_name=candidate.name,
                build_source_kind=candidate.source_kind,
                build_source_name=candidate.source_name,
                build_source_url=candidate.source_url,
                candidate_id=candidate.candidate_id,
            )
        else:
            # Preserve candidate provenance without claiming a saved build belongs to
            # an open Recruit chair.
            changes.update(
                build_source_kind=candidate.source_kind,
                build_source_name=candidate.source_name,
                build_source_url=candidate.source_url,
                candidate_id=candidate.candidate_id,
            )

        if not chair.is_locked("gear") and not chair.planned_gear_sets:
            changes["planned_gear_sets"] = tuple(candidate.gear_sets)

        if (
            not chair.is_locked("mundus")
            and not _clean(chair.planned_mundus)
            and _clean(candidate.mundus)
        ):
            changes["planned_mundus"] = _clean(candidate.mundus)

        # Skill-package adoption remains deliberately deferred. Candidate skills are
        # evidence only until the later ESO Logs / skill-evidence pass is implemented.
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
            field_changes = self._candidate_changes(chair, candidate)
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
