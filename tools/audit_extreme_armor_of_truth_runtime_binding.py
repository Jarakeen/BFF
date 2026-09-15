from __future__ import annotations

"""Prove the canonical Armor of Truth runtime trigger through the shared gear path."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from minmax.gear_set_repository import GearSetRepository
from services.extreme_dual_bar_gear_runtime_legality_service import (
    ExtremeDualBarGearRuntimeLegalityService,
)
from services.extreme_dual_bar_set_activation_evidence_service import (
    ExtremeDualBarSetActivationEvidence,
    ExtremeDualBarSetActivationEvidenceCatalog,
    ExtremeDualBarSetActivationScope,
)
from services.extreme_power_record_runtime_snapshot_witness_service import (
    ExtremePowerRecordRuntimeSnapshotWitnessService,
)

DATABASE = ROOT / "data" / "eso.db"


def main() -> int:
    repository = GearSetRepository(DATABASE)
    gear_set = repository.get_set("Armor of Truth")
    print("EXTREME ARMOR OF TRUTH GENERIC RUNTIME BINDING")
    print(f"database={DATABASE}")
    if gear_set is None:
        print("armor_of_truth_set_present=False")
        print("generic_armor_of_truth_trigger_binding_closed=False")
        return 2

    resolver = GearSetEffectVariantResolver(repository)
    effects = tuple(resolver.resolve(int(gear_set.id), 5))
    candidates = tuple(
        effect
        for effect in effects
        if effect.name == "weapon_spell_damage"
        and effect.trigger == "damage_off_balance_target"
    )
    print("armor_of_truth_set_present=True")
    print(f"resolved_effect_count={len(effects)}")
    print(f"matching_runtime_effect_count={len(candidates)}")

    effect = candidates[0] if len(candidates) == 1 else None
    if effect is not None:
        print(f"runtime_effect_name={effect.name!r}")
        print(f"runtime_effect_magnitude={float(effect.magnitude or 0.0):.3f}")
        print(f"runtime_effect_duration={float(effect.duration or 0.0):.3f}")
        print(f"runtime_effect_trigger={effect.trigger!r}")
        print(f"runtime_effect_target_type={None if effect.target_type is None else effect.target_type.value!r}")
        print(f"runtime_effect_source_persistence={None if effect.source_persistence is None else effect.source_persistence.value!r}")

    activation = ExtremeDualBarSetActivationEvidenceCatalog(
        evidence=(
            ExtremeDualBarSetActivationEvidence(
                set_id=int(gear_set.id),
                set_name=str(gear_set.name),
                category=str(gear_set.category or ""),
                front_count=5,
                back_count=5,
                front_active_breakpoints=(2, 3, 4, 5),
                back_active_breakpoints=(2, 3, 4, 5),
                activation_scope=ExtremeDualBarSetActivationScope.BOTH,
                weapon_only_two_piece=False,
            ),
        ),
    )
    witness = ExtremePowerRecordRuntimeSnapshotWitnessService.build("weapon_damage")
    runtime = ExtremeDualBarGearRuntimeLegalityService(resolver=resolver).resolve_history(
        activation,
        attempts=witness.snapshot.bar_effect_attempts,
        snapshot_time_seconds=witness.snapshot.snapshot_time_seconds,
        snapshot_active_bar=witness.active_bar,
        bar_transitions=witness.snapshot.bar_transitions,
        bar_transition_history_complete=witness.snapshot.bar_transition_history_complete,
    )
    active = tuple(
        row
        for row in runtime.active_effects
        if row.name == "weapon_spell_damage"
        and abs(float(row.magnitude or 0.0) - 460.0) <= 1e-9
    )

    checks = {
        "single_matching_runtime_effect": len(candidates) == 1,
        "runtime_effect_magnitude_is_460": effect is not None and abs(float(effect.magnitude or 0.0) - 460.0) <= 1e-9,
        "runtime_effect_duration_is_10s": effect is not None and abs(float(effect.duration or 0.0) - 10.0) <= 1e-9,
        "runtime_effect_target_is_self": effect is not None and getattr(effect.target_type, "value", None) == "self",
        "runtime_projection_unresolved_empty": runtime.unresolved == (),
        "runtime_projection_active_effect_present": len(active) == 1,
        "runtime_projection_not_misclassified_as_named_buff": "Armor of Truth" not in runtime.active_buffs,
    }

    print()
    print("RUNTIME PROJECTION")
    print(f"attempts_reviewed={runtime.attempts_reviewed}")
    print(f"active_named_buffs={runtime.active_buffs!r}")
    print(f"active_effect_count={len(runtime.active_effects)}")
    print(f"unresolved_count={len(runtime.unresolved)}")
    for message in runtime.unresolved:
        print(f"  unresolved: {message}")

    print()
    print("PROOF STATUS")
    for name, passed in checks.items():
        print(f"{name}={passed}")
    closed = all(checks.values())
    print(f"generic_armor_of_truth_trigger_binding_closed={closed}")
    print("final_e1_runtime_record_bridge_closed=False")
    print(
        "NEXT_STEP=if generic binding is closed, route the constructive Weapon/Spell witnesses through "
        "ExtremeRuntimeSnapshotCombatStateService with real Armor of Truth activation evidence and "
        "remove the narrow injected Armor of Truth adapter from the witness integration test"
    )
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
