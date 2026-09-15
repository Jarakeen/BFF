from __future__ import annotations

"""Audit the canonical E1 runtime-history bridge for closed power records.

The record services now expose machine-readable prerequisite ownership and one
constructive ``ExtremeRuntimeSnapshot`` witness. Armor of Truth is also registered
through the generic timed gear-effect path, so this audit verifies that no runtime-
history prerequisite remains orphaned behind prose or an objective-specific adapter.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.external_group_buff_provenance import ExternalGroupBuffApplication
from minmax.gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from minmax.gear_set_repository import GearSetRepository
from services.extreme_power_record_runtime_requirement_service import (
    ExtremePowerRequirementOwner,
)
from services.extreme_runtime_bar_effect_attempt import ExtremeRuntimeBarEffectAttempt
from services.extreme_runtime_snapshot import ExtremeRuntimePotionUse
from services.extreme_spell_damage_record_service import ExtremeSpellDamageRecordService
from services.extreme_weapon_damage_record_service import ExtremeWeaponDamageRecordService

DATABASE = ROOT / "data" / "eso.db"


def _audit(service) -> bool:
    objective_key = service.OBJECTIVE_KEY
    requirements = service.runtime_requirements()
    witness = service.runtime_witness()
    snapshot = witness.snapshot
    history = snapshot.ordered_runtime_history

    gear = tuple(row for row in history if isinstance(row, ExtremeRuntimeBarEffectAttempt))
    potions = tuple(row for row in history if isinstance(row, ExtremeRuntimePotionUse))
    external = tuple(row for row in history if isinstance(row, ExternalGroupBuffApplication))
    runtime_requirements = tuple(
        row for row in requirements if row.owner is ExtremePowerRequirementOwner.RUNTIME_HISTORY
    )

    repository = GearSetRepository(DATABASE)
    armor = repository.get_set("Armor of Truth")
    resolved = () if armor is None else tuple(GearSetEffectVariantResolver(repository).resolve(int(armor.id), 5))
    armor_effects = tuple(
        effect
        for effect in resolved
        if effect.name == "weapon_spell_damage"
        and abs(float(effect.magnitude or 0.0) - 460.0) <= 1e-12
        and effect.trigger == "damage_off_balance_target"
        and abs(float(effect.duration or 0.0) - 10.0) <= 1e-12
    )

    ordered = tuple(snapshot._entry_order(row) for row in history)
    checks = {
        "record_runtime_requirement_count_is_9": len(requirements) == 9,
        "runtime_history_requirement_count_is_3": len(runtime_requirements) == 3,
        "witness_closed": witness.closed,
        "single_armor_of_truth_trigger": len(gear) == 1,
        "single_potion_activation": len(potions) == 1,
        "single_external_minor_power_application": len(external) == 1,
        "runtime_history_ordered": ordered == tuple(sorted(ordered)),
        "bar_transition_history_complete": snapshot.bar_transition_history_complete,
        "generic_armor_of_truth_trigger_binding_closed": len(armor_effects) == 1,
        "record_objective_matches_witness": witness.objective_key == objective_key,
    }

    print(f"OBJECTIVE={objective_key}")
    print(f"requirement_count={len(requirements)}")
    print(f"runtime_history_requirement_count={len(runtime_requirements)}")
    print(f"history_entry_count={len(history)}")
    print(f"snapshot_time_seconds={snapshot.snapshot_time_seconds:.3f}")
    print(f"active_bar={witness.active_bar!r}")
    for name, passed in checks.items():
        print(f"{name}={passed}")
    print()
    return all(checks.values())


def main() -> int:
    print("EXTREME POWER RECORD E1 RUNTIME BRIDGE")
    print(f"database={DATABASE}")
    print()

    weapon = _audit(ExtremeWeaponDamageRecordService())
    spell = _audit(ExtremeSpellDamageRecordService())
    closed = weapon and spell

    print("PROOF STATUS")
    print(f"power_record_constructive_runtime_snapshot_ready={closed}")
    print(f"generic_armor_of_truth_trigger_binding_closed={closed}")
    print(f"final_e1_runtime_record_bridge_closed={closed}")
    print(
        "NEXT_STEP=if the E1 power-record bridge is closed, keep target health/Off Balance, same-build resource, class-runtime, and active-bar legality with their canonical owners and move to the next shared Extreme runtime gap rather than adding more objective-specific power plumbing"
    )
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
