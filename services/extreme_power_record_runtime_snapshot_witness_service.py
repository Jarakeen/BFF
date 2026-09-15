from __future__ import annotations

"""Construct ordered E1 runtime witnesses for the closed power records.

This service owns witness construction only.  It does not score Weapon/Spell Damage
and it does not move target-health, Off Balance target state, class-runtime mastery,
resource coupling, or active-bar legality into CombatState.

The ordered history deliberately contains only evidence already owned by the unified
runtime snapshot contract:

* an Armor of Truth gear-proc trigger attempt with active-bar provenance;
* one explicit potion activation;
* one explicitly proven external Minor power application.

The caller still supplies canonical dual-bar set activation evidence to the shared
runtime projector.  That keeps set ownership/slot legality separate from event history.
"""

from dataclasses import dataclass

from minmax.external_group_buff_provenance import ExternalGroupBuffApplication
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from minmax.support_target_type import SupportTargetType
from services.extreme_runtime_bar_effect_attempt import ExtremeRuntimeBarEffectAttempt
from services.extreme_runtime_snapshot import ExtremeRuntimePotionUse, ExtremeRuntimeSnapshot


@dataclass(frozen=True)
class ExtremePowerRecordRuntimeSnapshotWitness:
    objective_key: str
    snapshot: ExtremeRuntimeSnapshot
    active_bar: str
    expected_runtime_buffs: tuple[str, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def closed(self) -> bool:
        return not self.unresolved


class ExtremePowerRecordRuntimeSnapshotWitnessService:
    """Build one deterministic runtime-history witness for a closed power record."""

    _POWER_BUFF = {
        "weapon_damage": ("Minor Brutality", "Weapon Power potion"),
        "spell_damage": ("Minor Sorcery", "Spell Power potion"),
    }

    @classmethod
    def build(
        cls,
        objective_key: str,
        *,
        recipient_actor_id: str = "extreme_power_winner",
        external_source_actor_id: str = "group_power_provider",
        active_bar: str = "front",
        armor_of_truth_trigger_time_seconds: float = 10.0,
        potion_use_time_seconds: float = 11.0,
        external_buff_time_seconds: float = 12.0,
        snapshot_time_seconds: float = 15.0,
    ) -> ExtremePowerRecordRuntimeSnapshotWitness:
        key = str(objective_key or "").strip().casefold()
        profile = cls._POWER_BUFF.get(key)
        if profile is None:
            return ExtremePowerRecordRuntimeSnapshotWitness(
                objective_key=key,
                snapshot=ExtremeRuntimeSnapshot(snapshot_time_seconds=max(0.0, float(snapshot_time_seconds))),
                active_bar=str(active_bar or "front"),
                expected_runtime_buffs=(),
                unresolved=(f"Unsupported power record objective: {objective_key}",),
            )

        minor_buff, _potion_label = profile
        bar = "back" if str(active_bar or "front").strip().casefold() == "back" else "front"
        trigger_time = float(armor_of_truth_trigger_time_seconds)
        potion_time = float(potion_use_time_seconds)
        external_time = float(external_buff_time_seconds)
        snapshot_time = float(snapshot_time_seconds)

        unresolved: list[str] = []
        if trigger_time > snapshot_time:
            unresolved.append("Armor of Truth trigger occurs after the requested snapshot")
        if snapshot_time - trigger_time > 10.0 + 1e-12:
            unresolved.append("Armor of Truth 10-second runtime window has expired at the requested snapshot")
        if potion_time > snapshot_time:
            unresolved.append("Power potion activation occurs after the requested snapshot")
        if external_time > snapshot_time:
            unresolved.append("External Minor power application occurs after the requested snapshot")

        trigger_attempt = RuntimeEffectEventAttempt(
            RuntimeEvent(
                time_seconds=trigger_time,
                trigger="damage_off_balance_target",
                source="Armor of Truth reviewed 5pc trigger",
                sequence=0,
            )
        )
        history = (
            ExtremeRuntimeBarEffectAttempt(
                attempt=trigger_attempt,
                active_bar=bar,
            ),
            ExtremeRuntimePotionUse(potion_time, sequence=0),
            ExternalGroupBuffApplication(
                source_actor_id=external_source_actor_id,
                recipient_actor_id=recipient_actor_id,
                buff_name=minor_buff,
                target_type=SupportTargetType.SELF_OR_ALLY,
                applied_at_seconds=external_time,
                duration_seconds=20.0,
                source_evidence=f"reviewed external {minor_buff} application",
            ),
        )
        snapshot = ExtremeRuntimeSnapshot(
            runtime_history=history,
            snapshot_time_seconds=snapshot_time,
            recipient_actor_id=recipient_actor_id,
            group_member_ids=(recipient_actor_id, external_source_actor_id),
            bar_transition_history_complete=True,
        )
        expected = (
            "Armor of Truth",
            minor_buff,
        )
        return ExtremePowerRecordRuntimeSnapshotWitness(
            objective_key=key,
            snapshot=snapshot,
            active_bar=bar,
            expected_runtime_buffs=expected,
            unresolved=tuple(unresolved),
        )


__all__ = [
    "ExtremePowerRecordRuntimeSnapshotWitness",
    "ExtremePowerRecordRuntimeSnapshotWitnessService",
]
