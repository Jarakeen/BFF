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
class CompPlanHealth:
    required_effects: tuple[str, ...]
    covered_required: tuple[str, ...]
    conditional_required: tuple[str, ...]
    missing_required: tuple[str, ...]
    duplicate_effects: tuple[str, ...]
    open_player_seats: tuple[str, ...]
    open_gear_seats: tuple[str, ...]
    coverage_status: tuple[tuple[str, str], ...]
    providers_by_effect: tuple[tuple[str, tuple[str, ...]], ...]

    @property
    def planned_or_static_required_count(self) -> int:
        return len(self.covered_required) + len(self.conditional_required)


class CompPlanHealthService:
    """Evaluate exactly the state Comp Maker will save, not legacy UI projections."""

    def __init__(self, database_path: Path) -> None:
        self.planned_gear = RaidPlannedGearCoverageService(database_path)

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
        missing_required = tuple(
            name
            for name in _REQUIRED_EFFECTS
            if snapshot.status.get(name) not in {"available", "conditional"}
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

        return CompPlanHealth(
            required_effects=_REQUIRED_EFFECTS,
            covered_required=covered_required,
            conditional_required=conditional_required,
            missing_required=missing_required,
            duplicate_effects=duplicate_effects,
            open_player_seats=open_player_seats,
            open_gear_seats=open_gear_seats,
            coverage_status=tuple(
                (name, snapshot.status.get(name, "unverified"))
                for name in _EFFECT_NAMES
            ),
            providers_by_effect=tuple(provider_rows),
        )


__all__ = ["CompPlanHealth", "CompPlanHealthService"]
