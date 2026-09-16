from __future__ import annotations

from dataclasses import dataclass

from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.named_combat_buffs import NamedBuffEffect
from minmax.stat_ids import StatId
from services.extreme_movement_state_service import ExtremeMovementStateInputs


@dataclass(frozen=True)
class ExtremeMovementSourceProjection:
    inputs: ExtremeMovementStateInputs
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeMovementSourceProjectionService:
    """Compose reviewed movement effects into the shared movement-state contract.

    ESO's movement equations keep Buff, Skill, Item, Set, Mundus and CP channels
    separate even when several are additive. Extreme therefore preserves source
    ownership here and delegates the final equation to ``ExtremeMovementStateService``.
    Future source discovery should feed this adapter rather than recalculating
    movement in each optimizer family.
    """

    @staticmethod
    def _percent_effect_ratio(effect: Effect) -> tuple[float | None, str | None]:
        source = str(effect.source or "movement source")
        if effect.stat not in {StatId.MOVEMENT_SPEED, StatId.SPRINT_SPEED, StatId.SNEAK_SPEED}:
            stat = "none" if effect.stat is None else effect.stat.value
            return None, f"{source}: non-movement effect {stat}"
        if effect.operation is not EffectOperation.ADD_PERCENT:
            return None, f"{source}: unsupported movement operation {effect.operation.value}"
        if effect.unit is not EffectUnit.PERCENT:
            return None, f"{source}: unsupported movement unit {effect.unit.value}"
        return float(effect.value) / 100.0, None

    @staticmethod
    def _named_buff_movement_ratio(
        effect: NamedBuffEffect,
        *,
        source: str,
    ) -> tuple[float | None, str | None]:
        if effect.stat is not StatId.MOVEMENT_SPEED:
            return None, f"{source}: non-movement named-buff effect {effect.stat.value}"
        if effect.bucket != "ratio_points":
            return None, f"{source}: unsupported movement named-buff bucket {effect.bucket}"
        return float(effect.value), None

    @classmethod
    def compose(
        cls,
        *,
        named_buff_effects: tuple[tuple[str, NamedBuffEffect], ...] = (),
        skill_effects: tuple[Effect, ...] = (),
        item_effects: tuple[Effect, ...] = (),
        set_effects: tuple[Effect, ...] = (),
        mundus_effects: tuple[Effect, ...] = (),
        cp_effects: tuple[Effect, ...] = (),
        base: ExtremeMovementStateInputs | None = None,
    ) -> ExtremeMovementSourceProjection:
        current = base or ExtremeMovementStateInputs()
        buff_movement = float(current.buff_movement_speed)
        skill_movement = float(current.skill_movement_speed)
        item_movement = float(current.item_movement_speed)
        set_movement = float(current.set_movement_speed)
        mundus_movement = float(current.mundus_movement_speed)
        cp_movement = float(current.cp_movement_speed)
        skill_sprint = float(current.skill_sprint_speed)
        set_sprint = float(current.set_sprint_speed)
        cp_sprint = float(current.cp_sprint_speed)
        skill_sneak = float(current.skill_sneak_speed)
        cp_sneak = float(current.cp_sneak_speed)
        evidence: list[str] = []
        unresolved: list[str] = []

        for source, effect in named_buff_effects:
            value, error = cls._named_buff_movement_ratio(effect, source=source)
            if error is not None:
                unresolved.append(error)
                continue
            assert value is not None
            buff_movement += value
            evidence.append(f"{source}: +{value:.3f} Buff.MovementSpeed")

        buckets = (
            ("Skill", skill_effects),
            ("Item", item_effects),
            ("Set", set_effects),
            ("Mundus", mundus_effects),
            ("CP", cp_effects),
        )
        for family, effects in buckets:
            for effect in effects:
                value, error = cls._percent_effect_ratio(effect)
                if error is not None:
                    unresolved.append(error)
                    continue
                assert value is not None
                if effect.stat is StatId.MOVEMENT_SPEED:
                    if family == "Skill":
                        skill_movement += value
                    elif family == "Item":
                        item_movement += value
                    elif family == "Set":
                        set_movement += value
                    elif family == "Mundus":
                        mundus_movement += value
                    elif family == "CP":
                        cp_movement += value
                    evidence.append(f"{effect.source}: +{value:.3f} {family}.MovementSpeed")
                elif effect.stat is StatId.SPRINT_SPEED:
                    if family == "Skill":
                        skill_sprint += value
                    elif family == "Set":
                        set_sprint += value
                    elif family == "CP":
                        cp_sprint += value
                    else:
                        unresolved.append(
                            f"{effect.source}: {family}.SprintSpeed has no reviewed canonical formula bucket"
                        )
                        continue
                    evidence.append(f"{effect.source}: +{value:.3f} {family}.SprintSpeed")
                elif effect.stat is StatId.SNEAK_SPEED:
                    if family == "Skill":
                        skill_sneak += value
                    elif family == "CP":
                        cp_sneak += value
                    else:
                        unresolved.append(
                            f"{effect.source}: {family}.SneakSpeed has no reviewed canonical formula bucket"
                        )
                        continue
                    evidence.append(f"{effect.source}: +{value:.3f} {family}.SneakSpeed")

        inputs = ExtremeMovementStateInputs(
            base_walk_speed=current.base_walk_speed,
            buff_movement_speed=buff_movement,
            skill_movement_speed=skill_movement,
            item_movement_speed=item_movement,
            set_movement_speed=set_movement,
            mundus_movement_speed=mundus_movement,
            cp_movement_speed=cp_movement,
            set_sprint_speed=set_sprint,
            buff_sprint_speed=current.buff_sprint_speed,
            skill_sprint_speed=skill_sprint,
            cp_sprint_speed=cp_sprint,
            skill_normal_sneak_speed=current.skill_normal_sneak_speed,
            cp_sneak_speed=cp_sneak,
            skill_sneak_speed=skill_sneak,
            skill2_sneak_speed=current.skill2_sneak_speed,
        )
        return ExtremeMovementSourceProjection(
            inputs=inputs,
            evidence=tuple(evidence),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeMovementSourceProjection",
    "ExtremeMovementSourceProjectionService",
]
