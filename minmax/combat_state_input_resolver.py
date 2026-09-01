from __future__ import annotations

from dataclasses import replace

from models.build_model import PlayerBuild

from .base_character_state import PercentContribution
from .champion_point_static_repository import ChampionPointStaticRepository
from .combat_state import CombatState
from .derived_stats import StatContribution
from .gear_stat_inputs import CORE_FIELDS, GearCalculationInputs, GearStatInputResolver
from .named_combat_buffs import effects_for_buff, is_component_layer_buff
from .stat_ids import StatId


_RESOURCE_FIELDS = {
    StatId.MAX_HEALTH: "health",
    StatId.MAX_MAGICKA: "magicka",
    StatId.MAX_STAMINA: "stamina",
    StatId.HEALTH_RECOVERY: "health_recovery",
    StatId.MAGICKA_RECOVERY: "magicka_recovery",
    StatId.STAMINA_RECOVERY: "stamina_recovery",
}


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

    @staticmethod
    def _apply_named_buffs(
        result: GearCalculationInputs,
        combat_state: CombatState,
    ) -> GearCalculationInputs:
        unresolved = list(result.unresolved)
        applied = result.applied_effect_count

        for buff_name in combat_state.active_buffs:
            effects = effects_for_buff(
                buff_name,
                game_update=combat_state.game_update,
                allow_legacy_alias=False,
            )
            if not effects:
                # Known component-layer buffs are intentionally resolved later
                # by the damage/healing/shield pipeline that owns their meaning.
                if is_component_layer_buff(buff_name):
                    continue
                unresolved.append(
                    f"Active combat buff not stat-mapped for {combat_state.game_update.value}: {buff_name}"
                )
                continue

            source = f"Combat buff: {buff_name} [{combat_state.game_update.value}]"
            for effect in effects:
                if effect.bucket == "resource_percent":
                    field_name = _RESOURCE_FIELDS.get(effect.stat)
                    if field_name is None:
                        unresolved.append(f"{source}: unsupported resource stat {effect.stat.value}")
                        continue
                    current = getattr(result, field_name)
                    updated = replace(
                        current,
                        buff_percent_contributions=current.buff_percent_contributions
                        + (PercentContribution(source, effect.value),),
                    )
                    result = replace(result, **{field_name: updated})
                    applied += 1
                    continue

                field_name = CORE_FIELDS.get(effect.stat)
                if field_name is None:
                    unresolved.append(f"{source}: unsupported core stat {effect.stat.value}")
                    continue

                current = getattr(result.core, field_name)
                value = effect.value
                bucket = effect.bucket
                if bucket == "critical_rating":
                    value = GearStatInputResolver.critical_rating_to_ratio(value)
                    bucket = "flat"

                contribution = StatContribution(source, value)
                if bucket == "flat":
                    updated = replace(current, flat=current.flat + (contribution,))
                elif bucket == "percent":
                    updated = replace(current, percent=current.percent + (contribution,))
                elif bucket == "ratio_points":
                    updated = replace(
                        current,
                        additive_after_percent=current.additive_after_percent + (contribution,),
                    )
                else:
                    unresolved.append(f"{source}: unsupported buff bucket {effect.bucket}")
                    continue

                result = replace(result, core=replace(result.core, **{field_name: updated}))
                applied += 1

        return replace(result, applied_effect_count=applied, unresolved=tuple(unresolved))

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
        result = self._apply_named_buffs(result, combat_state)
        return self._apply_bracing_anchor(result, build, combat_state)
