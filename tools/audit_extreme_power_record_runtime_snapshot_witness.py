from __future__ import annotations

"""Audit constructive E1 runtime-history witnesses for the closed power records.

This audit proves that each record can be represented by one ordered
``ExtremeRuntimeSnapshot`` for all runtime-history-owned prerequisites.  It does not
claim the generic gear-trigger catalog can yet bind Armor of Truth automatically;
that source-neutral binding remains the one explicit E1 bridge gap.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.external_group_buff_provenance import ExternalGroupBuffApplication
from services.extreme_power_record_runtime_snapshot_witness_service import (
    ExtremePowerRecordRuntimeSnapshotWitnessService,
)
from services.extreme_runtime_bar_effect_attempt import ExtremeRuntimeBarEffectAttempt
from services.extreme_runtime_snapshot import ExtremeRuntimePotionUse


def _audit(objective_key: str) -> bool:
    witness = ExtremePowerRecordRuntimeSnapshotWitnessService.build(objective_key)
    snapshot = witness.snapshot
    history = snapshot.ordered_runtime_history

    gear = tuple(row for row in history if isinstance(row, ExtremeRuntimeBarEffectAttempt))
    potions = tuple(row for row in history if isinstance(row, ExtremeRuntimePotionUse))
    external = tuple(row for row in history if isinstance(row, ExternalGroupBuffApplication))

    gear_shape_ok = (
        len(gear) == 1
        and gear[0].attempt.event.trigger == "damage_off_balance_target"
        and gear[0].attempt.event.source == "Armor of Truth reviewed 5pc trigger"
    )
    potion_shape_ok = len(potions) == 1
    external_shape_ok = len(external) == 1
    recipient_proven = (
        snapshot.recipient_actor_id is not None
        and snapshot.recipient_actor_id in snapshot.group_member_ids
        and external
        and external[0].source_actor_id in snapshot.group_member_ids
    )
    ordered = tuple(snapshot._entry_order(row) for row in history)
    ordering_ok = ordered == tuple(sorted(ordered))
    in_window = (
        gear
        and snapshot.snapshot_time_seconds - gear[0].time_seconds <= 10.0 + 1e-12
    )

    checks = {
        "witness_closed": witness.closed,
        "single_armor_of_truth_trigger": gear_shape_ok,
        "single_potion_activation": potion_shape_ok,
        "single_external_minor_power_application": external_shape_ok,
        "external_group_provenance_complete": bool(recipient_proven),
        "runtime_history_ordered": ordering_ok,
        "armor_of_truth_window_active": bool(in_window),
        "bar_transition_history_complete": snapshot.bar_transition_history_complete,
    }

    print(f"OBJECTIVE={objective_key}")
    print(f"history_entry_count={len(history)}")
    print(f"snapshot_time_seconds={snapshot.snapshot_time_seconds:.3f}")
    print(f"active_bar={witness.active_bar!r}")
    print(f"expected_runtime_buffs={witness.expected_runtime_buffs!r}")
    for name, passed in checks.items():
        print(f"{name}={passed}")
    print("generic_armor_of_truth_trigger_binding_closed=False")
    print("  gap: reviewed Armor of Truth trigger semantics are proven, but the generic gear runtime catalog does not yet bind the source-neutral damage_off_balance_target attempt to the set proc without an adapter")
    print()
    return all(checks.values())


def main() -> int:
    print("EXTREME POWER RECORD CONSTRUCTIVE RUNTIME SNAPSHOT WITNESS")
    print()
    weapon = _audit("weapon_damage")
    spell = _audit("spell_damage")
    constructive = weapon and spell
    print("PROOF STATUS")
    print(f"power_record_constructive_runtime_snapshot_ready={constructive}")
    print("generic_armor_of_truth_trigger_binding_closed=False")
    print("final_e1_runtime_record_bridge_closed=False")
    print(
        "NEXT_STEP=if constructive witnesses are green, add a canonical source-neutral Armor of Truth gear-trigger binding to the shared gear runtime path; then rerun the same witnesses without an injected adapter before promoting the record services to runtime-snapshot consumers"
    )
    return 0 if constructive else 2


if __name__ == "__main__":
    raise SystemExit(main())
