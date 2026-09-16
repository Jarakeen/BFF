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

    This is deliberately source-family aware because ESO's movement equations do
    not put every bonus in the same bucket. Named Expedition belongs to the Buff
    movement bucket; The Steed belongs to the Mundus movement bucket. Future
    skill, set, item/trait, sprint-only, sneak-only and CP providers should enter
    through this same service rather than bypassing the canonical formulas.
    """

    @staticmethod
    def _mundus_movement_ratio(effect: Effect) -> tuple[float | None, str | None]:
        source = str(effect.source or "Mundus")
        if effect.stat is not StatId.MOVEMENT_SPEED:
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
        mundus_effects: tuple[Effect, ...] = (),
        base: ExtremeMovementStateInputs | None = None,
    ) -> ExtremeMovementSourceProjection:
        current = base or ExtremeMovementStateInputs()
        buff_movement = float(current.buff_movement_speed)
        mundus_movement = float(current.mundus_movement_speed)
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

        for effect in mundus_effects:
            value, error = cls._mundus_movement_ratio(effect)
            if error is not None:
                unresolved.append(error)
                continue
            assert value is not None
            mundus_movement += value
            evidence.append(f"{effect.source}: +{value:.3f} Mundus.MovementSpeed")

        inputs = ExtremeMovementStateInputs(
            base_walk_speed=current.base_walk_speed,
            buff_movement_speed=buff_movement,
            skill_movement_speed=current.skill_movement_speed,
            item_movement_speed=current.item_movement_speed,
            set_movement_speed=current.set_movement_speed,
            mundus_movement_speed=mundus_movement,
            cp_movement_speed=current.cp_movement_speed,
            set_sprint_speed=current.set_sprint_speed,
            buff_sprint_speed=current.buff_sprint_speed,
            skill_sprint_speed=current.skill_sprint_speed,
            cp_sprint_speed=current.cp_sprint_speed,
            skill_normal_sneak_speed=current.skill_normal_sneak_speed,
            cp_sneak_speed=current.cp_sneak_speed,
            skill_sneak_speed=current.skill_sneak_speed,
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
