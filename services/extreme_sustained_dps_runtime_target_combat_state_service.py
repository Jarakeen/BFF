from __future__ import annotations

"""Project enemy-target runtime EffectVariants into canonical CombatState."""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant
from minmax.combat_damage_modifiers import damage_taken_from_target_state
from minmax.combat_state import CombatState
from minmax.combat_target_critical_damage import (
    critical_damage_taken_percent_from_target_state,
)
from minmax.combat_target_resistance import resistance_reduction_from_target_state
from minmax.named_combat_buffs import canonical_buff_name
from minmax.runtime_effect_stream import process_effect_variant_runtime_stream
from minmax.runtime_effect_window import partition_runtime_effect_windows
from minmax.support_target_type import SupportTargetType
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeTargetCombatStateResult:
    combat_state: CombatState
    explicit_resistance_reduction: float = 0.0
    unresolved: tuple[str, ...] = ()


class ExtremeSustainedDPSRuntimeTargetCombatStateService:
    """Resolve exact target-side named Damage Taken state at one ordered instant."""

    @staticmethod
    def resolve(
        *,
        snapshot: ExtremeRuntimeSnapshot,
        effects: tuple[EffectVariant, ...],
        target_identity: str,
    ) -> ExtremeSustainedDPSRuntimeTargetCombatStateResult:
        target = str(target_identity or "").strip()
        if not target:
            return ExtremeSustainedDPSRuntimeTargetCombatStateResult(
                CombatState(),
                0.0,
                ("Runtime target combat-state projection requires target identity",),
            )

        active_buffs: list[str] = []
        explicit_resistance_reduction = 0.0
        unresolved: list[str] = []
        attempts = tuple(snapshot.effect_attempts)

        for effect in tuple(effects):
            if effect.target_type is not SupportTargetType.ENEMY:
                continue
            canonical = canonical_buff_name(str(effect.name or "").replace("_", " "))

            if canonical is None:
                damage_taken_probe = 0.0
                resistance_probe = 0.0
                critical_damage_probe = 0.0
            else:
                probe_state = CombatState(active_buffs=(canonical,))
                damage_taken_probe = damage_taken_from_target_state(probe_state).generic
                resistance_probe = resistance_reduction_from_target_state(probe_state)
                critical_damage_probe = (
                    critical_damage_taken_percent_from_target_state(probe_state)
                )

            explicit_resistance = (
                None
                if effect.resistance_reduction is None
                else float(effect.resistance_reduction)
            )
            if (
                abs(float(damage_taken_probe)) <= 1e-12
                and abs(float(resistance_probe)) <= 1e-12
                and abs(float(critical_damage_probe)) <= 1e-12
                and explicit_resistance is None
            ):
                continue

            stream = process_effect_variant_runtime_stream(attempts, effect)
            for step in stream.unresolved_steps:
                reasons = (
                    step.transition.unresolved
                    or step.transition.activation.eligibility.reasons
                )
                if reasons:
                    unresolved.append(
                        f"{effect.source} {canonical or effect.name} target runtime history unresolved: "
                        + ", ".join(reasons)
                    )

            partition = partition_runtime_effect_windows(
                stream.final_state.windows,
                at_time_seconds=snapshot.snapshot_time_seconds,
            )
            if any(
                window.effect_name == effect.name
                and str(window.target or "").strip() == target
                for window in partition.active
            ):
                if canonical is not None and (
                    abs(float(damage_taken_probe)) > 1e-12
                    or abs(float(resistance_probe)) > 1e-12
                    or abs(float(critical_damage_probe)) > 1e-12
                ):
                    active_buffs.append(canonical)
                if (
                    explicit_resistance is not None
                    and abs(float(resistance_probe)) <= 1e-12
                ):
                    explicit_resistance_reduction += explicit_resistance

        return ExtremeSustainedDPSRuntimeTargetCombatStateResult(
            combat_state=CombatState(
                in_combat=bool(active_buffs or attempts),
                active_buffs=tuple(dict.fromkeys(active_buffs)),
            ),
            explicit_resistance_reduction=float(explicit_resistance_reduction),
            unresolved=tuple(dict.fromkeys(row for row in unresolved if row)),
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeTargetCombatStateResult",
    "ExtremeSustainedDPSRuntimeTargetCombatStateService",
]
