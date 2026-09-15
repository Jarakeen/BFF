from __future__ import annotations

"""Bound Sorcerer Font of Power against the current Weapon Damage class frontier.

The previous joint class/bar audit deliberately omitted higher-Max-Resource input,
which means pure Sorcerer was undercounted. This audit uses the already proof-closed
Update 50 Max Magicka record as a conservative global upper bound, then finds the
minimum 1,750-resource breakpoint at which Sorcerer overtakes the strongest reviewed
non-Sorcerer pure-class route for each sampled Weapon Damage reference.

The 108,319 ceiling is NOT claimed as simultaneously realizable with the Weapon
Damage build. It is only a proof-safe upper bound used to decide whether Sorcerer
can be pruned or must remain in the exact same-build search.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.character_build.character_class import CharacterClass
from services.extreme_class_mastery_pair_service import ExtremeClassMasteryPairService

DATABASE = ROOT / "data" / "eso.db"
OBJECTIVE = "weapon_damage"
MAX_MAGICKA_GLOBAL_CEILING = 108_319.0
MAX_STAMINA_GLOBAL_CEILING = 101_930.0
HIGHER_RESOURCE_GLOBAL_CEILING = max(
    MAX_MAGICKA_GLOBAL_CEILING,
    MAX_STAMINA_GLOBAL_CEILING,
)
RESOURCE_STEP = 1750
REFERENCES = (1000.0, 2233.3333333333, 3000.0, 6000.0, 10000.0, 15000.0)


def _best_non_sorcerer(service: ExtremeClassMasteryPairService, reference: float):
    rows = []
    for base_class in CharacterClass:
        if base_class is CharacterClass.SORCERER:
            continue
        row = service.best_for_class(
            base_class,
            OBJECTIVE,
            reference_value=reference,
        )
        if row is not None and row.projected_delta is not None:
            rows.append(row)
    return max(
        rows,
        key=lambda row: (
            float(row.projected_delta or 0.0),
            row.base_class.value,
            row.passive_names,
        ),
        default=None,
    )


def _sorcerer(
    service: ExtremeClassMasteryPairService,
    reference: float,
    resource: float,
):
    return service.best_for_class(
        CharacterClass.SORCERER,
        OBJECTIVE,
        reference_value=reference,
        higher_max_resource=resource,
    )


def _minimum_winning_resource(
    service: ExtremeClassMasteryPairService,
    reference: float,
    incumbent_delta: float,
):
    max_complete_steps = int(HIGHER_RESOURCE_GLOBAL_CEILING // RESOURCE_STEP)
    for step in range(max_complete_steps + 1):
        resource = float(step * RESOURCE_STEP)
        row = _sorcerer(service, reference, resource)
        if row is None or row.projected_delta is None:
            continue
        if float(row.projected_delta) > incumbent_delta + 1e-9:
            return resource, row
    return None, None


def main() -> int:
    service = ExtremeClassMasteryPairService(DATABASE)

    print("EXTREME WEAPON DAMAGE RESOURCE-COUPLED CLASS FRONTIER")
    print(f"database={DATABASE}")
    print(f"objective={OBJECTIVE}")
    print(f"max_magicka_global_ceiling={MAX_MAGICKA_GLOBAL_CEILING:.0f}")
    print(f"max_stamina_global_ceiling={MAX_STAMINA_GLOBAL_CEILING:.0f}")
    print(f"higher_resource_global_ceiling={HIGHER_RESOURCE_GLOBAL_CEILING:.0f}")
    print("global_resource_ceiling_is_same_build_proof=False")
    print("resource_breakpoint_step=1750")
    print()

    sorcerer_remains_live = False
    for reference in REFERENCES:
        incumbent = _best_non_sorcerer(service, reference)
        if incumbent is None or incumbent.projected_delta is None:
            print(f"REFERENCE={reference:.3f}")
            print("  incumbent=<none>")
            continue

        incumbent_delta = float(incumbent.projected_delta)
        upper = _sorcerer(service, reference, HIGHER_RESOURCE_GLOBAL_CEILING)
        upper_delta = 0.0 if upper is None or upper.projected_delta is None else float(upper.projected_delta)
        threshold_resource, threshold_row = _minimum_winning_resource(
            service,
            reference,
            incumbent_delta,
        )
        can_overtake = threshold_resource is not None
        sorcerer_remains_live = sorcerer_remains_live or can_overtake

        print(f"REFERENCE={reference:.3f}")
        print(
            f"  incumbent class={incumbent.base_class.value} "
            f"delta={incumbent_delta:.3f} mastery={incumbent.passive_names!r}"
        )
        print(f"  sorcerer_global_ceiling_delta={upper_delta:.3f}")
        print(f"  sorcerer_can_overtake_under_global_resource_ceiling={can_overtake}")
        if threshold_resource is not None and threshold_row is not None:
            print(f"  minimum_winning_higher_max_resource={threshold_resource:.0f}")
            print(f"  winning_sorcerer_delta_at_threshold={float(threshold_row.projected_delta):.3f}")
            print(f"  winning_sorcerer_percent={float(threshold_row.percent):.3f}")
            print(f"  winning_sorcerer_mastery={threshold_row.passive_names!r}")
            for condition in threshold_row.conditions:
                print(f"    runtime: {condition}")
        print()

    print("FRONTIER SUMMARY")
    print(f"sorcerer_resource_coupling_requires_exact_same_build_search={sorcerer_remains_live}")
    print("final_weapon_damage_class_route_closed=False")
    print("final_weapon_damage_record_closed=False")
    print(
        "NEXT_STEP=project the actual higher Max Magicka/Stamina of competitive pure-Sorcerer "
        "Weapon Damage candidates and compare it to these finite resource thresholds before "
        "composing external named buffs and exact named gear"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
