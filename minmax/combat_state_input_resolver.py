from __future__ import annotations

from dataclasses import replace

from models.build_model import PlayerBuild

from .champion_point_static_repository import ChampionPointStaticRepository
from .combat_state import CombatState
from .gear_stat_inputs import GearCalculationInputs


class CombatStateInputResolver:
    """Apply explicitly active transient effects to otherwise static build inputs."""

    def __init__(self, champion_point_repository: ChampionPointStaticRepository | None = None) -> None:
        self.champion_point_repository = champion_point_repository

    @staticmethod
    def _saved_points(build: PlayerBuild, name: str) -> int | None:
        key = str(name).strip().casefold()
        for entry in build.ChampionPoints:
            if str(entry.Name or "").strip().casefold() != key:
                continue
            try:
                return max(0, int(str(entry.Points or "0").strip() or 0))
            except (TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _completed_stages(record, points: int) -> int:
        allocated = max(0, min(int(points), int(record.max_points or points)))
        thresholds = tuple(value for value in record.jump_points if value > 0)
        if thresholds:
            return sum(1 for value in thresholds if allocated >= value)
        return allocated

    def _apply_bracing_anchor(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        combat_state: CombatState,
    ) -> GearCalculationInputs:
        points = self._saved_points(build, "Bracing Anchor")
        if points is None:
            return result

        old_warning = "Champion Point is dynamic or not yet stat-mapped: Bracing Anchor"
        unresolved = [message for message in result.unresolved if message != old_warning]

        if self.champion_point_repository is None:
            unresolved.append("Bracing Anchor is slotted but Champion Point repository is unavailable")
            return replace(result, unresolved=tuple(unresolved))

        record = self.champion_point_repository.get("Bracing Anchor")
        if record is None:
            unresolved.append("Champion Point not found: Bracing Anchor")
            return replace(result, unresolved=tuple(unresolved))

        stages = self._completed_stages(record, points)
        if stages <= 0 or not combat_state.in_combat:
            return replace(result, unresolved=tuple(unresolved))

        # Current tooltip: +4% amount blocked per completed stage while in combat.
        amount = 0.04 * stages
        mitigation = replace(
            result.core.block_mitigation,
            amount_blocked_modifiers=result.core.block_mitigation.amount_blocked_modifiers
            + (("Champion Point: Bracing Anchor (in combat)", amount),),
        )
        return replace(
            result,
            core=replace(result.core, block_mitigation=mitigation),
            applied_effect_count=result.applied_effect_count + 1,
            unresolved=tuple(unresolved),
        )

    def apply(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        combat_state: CombatState = CombatState(),
    ) -> GearCalculationInputs:
        return self._apply_bracing_anchor(result, build, combat_state)
