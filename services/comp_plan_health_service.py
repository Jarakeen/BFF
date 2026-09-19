from __future__ import annotations

"""Canonical Comp Maker Team Health derived from CompPlanState only."""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from models.comp_plan_state import CompPlanState
from services.raid_group_effect_catalog import (
    GROUP_COVERAGE_BY_NAME,
    GROUP_COVERAGE_NAMES,
)
from services.raid_planned_gear_coverage_service import (
    PlannedGearCoverageProvider,
    RaidPlannedGearCoverageService,
)
from services.raid_planned_skill_coverage_service import (
    PlannedSkillCoverageProvider,
    RaidPlannedSkillCoverageService,
)
from services.raid_unique_support_set_catalog import (
    UNIQUE_SUPPORT_SET_BY_NAME,
    UNIQUE_SUPPORT_SET_NAMES,
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


_EFFECT_NAMES = tuple(
    dict.fromkeys((*GROUP_COVERAGE_NAMES, *UNIQUE_SUPPORT_SET_NAMES))
)
_REFERENCE_BY_NAME = {
    **GROUP_COVERAGE_BY_NAME,
    **UNIQUE_SUPPORT_SET_BY_NAME,
}
_REQUIRED_EFFECTS = tuple(
    name
    for name in _EFFECT_NAMES
    if bool(getattr(_REFERENCE_BY_NAME.get(name), "default_required", False))
)


@dataclass(frozen=True)
class CompAssignmentHealthReview:
    effect_name: str
    primary_seats: tuple[str, ...]
    backup_seats: tuple[str, ...]
    supported_primary: tuple[str, ...]
    unsupported_primary: tuple[str, ...]
    supported_backup: tuple[str, ...]
    duplicate_primary: bool
    state: str
    label: str


@dataclass(frozen=True)
class CompPlanHealth:
    required_effects: tuple[str, ...]
    covered_required: tuple[str, ...]
    conditional_required: tuple[str, ...]
    planned_required: tuple[str, ...]
    missing_required: tuple[str, ...]
    duplicate_effects: tuple[str, ...]
    open_player_seats: tuple[str, ...]
    open_gear_seats: tuple[str, ...]
    coverage_status: tuple[tuple[str, str], ...]
    providers_by_effect: tuple[tuple[str, tuple[str, ...]], ...]
    assignment_reviews: tuple[CompAssignmentHealthReview, ...]

    @property
    def planned_or_static_required_count(self) -> int:
        return len(self.planned_required)


def required_effect_names() -> tuple[str, ...]:
    """Return the current Comp Team Health default-required planning effects."""
    return _REQUIRED_EFFECTS


class CompPlanHealthService:
    """Evaluate exactly the state Comp Maker will save, not legacy UI projections."""

    def __init__(self, database_path: Path) -> None:
        self.planned_gear = RaidPlannedGearCoverageService(database_path)
        self.planned_skills = RaidPlannedSkillCoverageService(database_path)

    def _assignment_reviews(
        self,
        state: CompPlanState,
        *,
        providers_by_effect: tuple[tuple[str, tuple[str, ...]], ...],
    ) -> tuple[CompAssignmentHealthReview, ...]:
        available_effects = {name for name, providers in providers_by_effect if providers}
        effects_by_seat: dict[str, set[str]] = {}
        for chair in state.chairs:
            row = PlannedGearCoverageProvider(
                seat_id=chair.seat_id,
                provider_label=chair.character_name or chair.player_name or chair.seat_id,
                gear_sets=chair.planned_gear_sets,
            )
            effects_by_seat[chair.seat_id.casefold()] = set(
                self.planned_gear.effects_for_provider(
                    row,
                    effect_names=_EFFECT_NAMES,
                )
            )
            planned_skill = PlannedSkillCoverageProvider(
                seat_id=chair.seat_id,
                provider_label=chair.character_name or chair.player_name or chair.seat_id,
                eso_class=chair.eso_class,
                skills=chair.planned_skills,
            )
            effects_by_seat[chair.seat_id.casefold()].update(
                effect_name
                for effect_name, _source in self.planned_skills.effects_for_provider(
                    planned_skill,
                    effect_names=_EFFECT_NAMES,
                )
            )

        reviews: list[CompAssignmentHealthReview] = []
        for effect_name in _EFFECT_NAMES:
            primary = tuple(
                chair.seat_id
                for chair in state.chairs
                if _clean(chair.primary_assignment).casefold()
                == effect_name.casefold()
            )
            backup = tuple(
                chair.seat_id
                for chair in state.chairs
                if _clean(chair.secondary_assignment).casefold()
                == effect_name.casefold()
            )
            supported_primary = tuple(
                seat
                for seat in primary
                if effect_name in effects_by_seat.get(seat.casefold(), set())
            )
            unsupported_primary = tuple(
                seat for seat in primary if seat not in supported_primary
            )
            supported_backup = tuple(
                seat
                for seat in backup
                if effect_name in effects_by_seat.get(seat.casefold(), set())
            )
            duplicate_primary = len(primary) > 1

            if supported_primary:
                state_name = "assigned_conditional"
                label = "Covered • Planned source"
            elif primary:
                state_name = "assigned_unproven"
                label = "Covered • Planned"
            elif supported_backup:
                state_name = "backup_only"
                label = "Covered • Backup only"
            elif effect_name in available_effects:
                state_name = "unassigned_available"
                label = "Covered • Unassigned"
            else:
                state_name = "gap"
                label = "Missing • No provider"

            if duplicate_primary:
                label += " • Duplicate primary"

            reviews.append(
                CompAssignmentHealthReview(
                    effect_name=effect_name,
                    primary_seats=primary,
                    backup_seats=backup,
                    supported_primary=supported_primary,
                    unsupported_primary=unsupported_primary,
                    supported_backup=supported_backup,
                    duplicate_primary=duplicate_primary,
                    state=state_name,
                    label=label,
                )
            )
        return tuple(reviews)

    def evaluate(self, state: CompPlanState) -> CompPlanHealth:
        if not isinstance(state, CompPlanState):
            raise TypeError("Comp Team Health requires CompPlanState")

        planned_rows = tuple(
            PlannedGearCoverageProvider(
                seat_id=chair.seat_id,
                provider_label=(
                    chair.character_name
                    or chair.player_name
                    or chair.seat_id
                ),
                gear_sets=chair.planned_gear_sets,
            )
            for chair in state.chairs
            if chair.planned_gear_sets
        )
        snapshot = self.planned_gear.empty_snapshot(_EFFECT_NAMES)
        snapshot = self.planned_gear.overlay(
            snapshot,
            planned_rows,
            effect_names=_EFFECT_NAMES,
        )
        planned_skill_rows = tuple(
            PlannedSkillCoverageProvider(
                seat_id=chair.seat_id,
                provider_label=chair.character_name or chair.player_name or chair.seat_id,
                eso_class=chair.eso_class,
                skills=chair.planned_skills,
            )
            for chair in state.chairs
            if chair.planned_skills or chair.eso_class
        )
        snapshot = self.planned_skills.overlay(
            snapshot,
            planned_skill_rows,
            effect_names=_EFFECT_NAMES,
        )

        covered_required = tuple(
            name
            for name in _REQUIRED_EFFECTS
            if snapshot.status.get(name) == "available"
        )
        conditional_required = tuple(
            name
            for name in _REQUIRED_EFFECTS
            if snapshot.status.get(name) == "conditional"
        )
        provider_counts = Counter()
        provider_rows: list[tuple[str, tuple[str, ...]]] = []
        for name in _EFFECT_NAMES:
            providers = tuple(
                dict.fromkeys(
                    (
                        *tuple(snapshot.providers.get(name, ()) or ()),
                        *tuple(snapshot.conditional_providers.get(name, ()) or ()),
                    )
                )
            )
            if providers:
                provider_rows.append((name, providers))
                provider_counts[name] = len(providers)

        duplicate_effects = tuple(
            name
            for name in _EFFECT_NAMES
            if provider_counts.get(name, 0) > 1
        )
        open_player_seats = tuple(
            chair.seat_id
            for chair in state.chairs
            if chair.is_open_player
        )
        open_gear_seats = tuple(
            chair.seat_id
            for chair in state.chairs
            if chair.is_open_player and not chair.planned_gear_sets
        )

        assignment_reviews = self._assignment_reviews(
            state,
            providers_by_effect=tuple(provider_rows),
        )
        review_by_effect = {
            review.effect_name: review
            for review in assignment_reviews
        }
        planned_required = tuple(
            name
            for name in _REQUIRED_EFFECTS
            if review_by_effect[name].state != "gap"
        )
        missing_required = tuple(
            name
            for name in _REQUIRED_EFFECTS
            if review_by_effect[name].state == "gap"
        )

        return CompPlanHealth(
            required_effects=_REQUIRED_EFFECTS,
            covered_required=covered_required,
            conditional_required=conditional_required,
            planned_required=planned_required,
            missing_required=missing_required,
            duplicate_effects=duplicate_effects,
            open_player_seats=open_player_seats,
            open_gear_seats=open_gear_seats,
            coverage_status=tuple(
                (name, snapshot.status.get(name, "unverified"))
                for name in _EFFECT_NAMES
            ),
            providers_by_effect=tuple(provider_rows),
            assignment_reviews=assignment_reviews,
        )


__all__ = [
    "CompAssignmentHealthReview",
    "CompPlanHealth",
    "CompPlanHealthService",
    "required_effect_names",
]
