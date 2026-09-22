from __future__ import annotations

"""Project enemy-target runtime EffectVariants into canonical CombatState."""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant
from minmax.combat_damage_modifiers import damage_taken_from_target_state
from minmax.combat_state import CombatState
from minmax.combat_target_resistance import resistance_reduction_from_target_state
from minmax.named_combat_buffs import canonical_buff_name
from minmax.runtime_effect_stream import process_effect_variant_runtime_stream
from minmax.runtime_effect_window import partition_runtime_effect_windows
from minmax.support_target_type import SupportTargetType
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeTargetCombatStateResult:
    combat_state: CombatState
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
                ("Runtime target combat-state projection requires target identity",),
            )

        active_buffs: list[str] = []
        unresolved: list[str] = []
        attempts = tuple(snapshot.effect_attempts)

        for effect in tuple(effects):
            if effect.target_type is not SupportTargetType.ENEMY:
                continue
            canonical = canonical_buff_name(str(effect.name or "").replace("_", " "))
            if canonical is None:
                continue

            probe_state = CombatState(active_buffs=(canonical,))
            damage_taken_probe = damage_taken_from_target_state(probe_state)
            resistance_probe = resistance_reduction_from_target_state(probe_state)
            if (
                abs(float(damage_taken_probe.generic)) <= 1e-12
                and abs(float(resistance_probe)) <= 1e-12
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
                        f"{effect.source} {canonical} target runtime history unresolved: "
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
                active_buffs.append(canonical)

        return ExtremeSustainedDPSRuntimeTargetCombatStateResult(
            combat_state=CombatState(
                in_combat=bool(active_buffs or attempts),
                active_buffs=tuple(dict.fromkeys(active_buffs)),
            ),
            unresolved=tuple(dict.fromkeys(row for row in unresolved if row)),
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeTargetCombatStateResult",
    "ExtremeSustainedDPSRuntimeTargetCombatStateService",
]
