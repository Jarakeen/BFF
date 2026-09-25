from __future__ import annotations

"""Project exact-time SELF-target named runtime effects into canonical CombatState."""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant
from minmax.combat_state import CombatState
from minmax.named_combat_buffs import canonical_buff_name
from minmax.runtime_effect_stream import process_effect_variant_runtime_stream
from minmax.runtime_effect_window import partition_runtime_effect_windows
from minmax.support_target_type import SupportTargetType
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeSelfCombatStateResult:
    combat_state: CombatState
    unresolved: tuple[str, ...] = ()


class ExtremeSustainedDPSRuntimeSelfCombatStateService:
    """Resolve active SELF named effects without owning their numeric semantics."""

    @staticmethod
    def resolve(
        *,
        snapshot: ExtremeRuntimeSnapshot,
        effects: tuple[EffectVariant, ...],
    ) -> ExtremeSustainedDPSRuntimeSelfCombatStateResult:
        active_buffs: list[str] = []
        unresolved: list[str] = []
        attempts = tuple(snapshot.effect_attempts)

        for effect in tuple(effects):
            if effect.target_type is not SupportTargetType.SELF:
                continue

            canonical = canonical_buff_name(str(effect.name or "").replace("_", " "))
            if canonical is None:
                unresolved.append(
                    f"{effect.source} SELF runtime effect {effect.name!r} has no "
                    "canonical named-effect authority"
                )
                continue

            stream = process_effect_variant_runtime_stream(attempts, effect)
            for step in stream.unresolved_steps:
                reasons = (
                    step.transition.unresolved
                    or step.transition.activation.eligibility.reasons
                )
                if reasons:
                    unresolved.append(
                        f"{effect.source} {canonical} self runtime history unresolved: "
                        + ", ".join(reasons)
                    )

            partition = partition_runtime_effect_windows(
                stream.final_state.windows,
                at_time_seconds=snapshot.snapshot_time_seconds,
            )
            if any(window.effect_name == effect.name for window in partition.active):
                active_buffs.append(canonical)

        return ExtremeSustainedDPSRuntimeSelfCombatStateResult(
            combat_state=CombatState(
                in_combat=bool(active_buffs or attempts),
                active_buffs=tuple(dict.fromkeys(active_buffs)),
            ),
            unresolved=tuple(dict.fromkeys(row for row in unresolved if row)),
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeSelfCombatStateResult",
    "ExtremeSustainedDPSRuntimeSelfCombatStateService",
]
