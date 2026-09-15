from __future__ import annotations

"""Add the reviewed pure-Sorcerer active-bar passive to the same-build frontier.

The preceding named-gear same-build audit proves legal resolved gear/resource states
for pure Sorcerer, but its Class Mastery comparison intentionally omitted the separate
Expert Mage active-bar passive. This audit reuses those same physical gear/resource
witnesses, adds the best reviewed six-slot pure-Sorcerer Expert Mage allocation before
Class Mastery percentage scoring, and compares the resulting Sorcerer total against
the strongest reviewed non-Sorcerer pure-class mastery route at the same pre-class
Weapon Damage baseline.

No independent Max Resource maximum is mixed in. Resource scoring, metadata-warning
reconciliation, set legality, and the reviewed Weapon Damage subtotal are all reused
from the existing audits/services.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.character_build.character_class import CharacterClass
from services.extreme_class_mastery_pair_service import ExtremeClassMasteryPairService
from services.extreme_hypothetical_class_progression_service import (
    ExtremeHypotheticalClassProgressionService,
)
from services.extreme_optimization_service import ExtremeOptimizationService
from services.extreme_structural_core_stat_record_service import (
    ExtremeCanonicalStructuralStatEvaluator,
)
from services.extreme_subclass_slot_allocation_service import (
    ExtremeSubclassSlotAllocationService,
)
from tools.audit_extreme_weapon_damage_physical_gear_resource_requirements import (
    _best_non_sorcerer,
    _nongear_preclass_weapon_damage,
)
from tools.audit_extreme_weapon_damage_preweapon_upper_bound import _race_ceiling
from tools.audit_extreme_weapon_damage_sorcerer_free_resource_witness import (
    _pure_sorcerer_route,
    _weapon_damage_mundus_name,
)
from tools.audit_extreme_weapon_damage_sorcerer_named_gear_same_build import (
    DATABASE,
    WEAPON_OBJECTIVE,
    _best_resource_for_witness,
    _physical_frontier_with_witnesses,
)


def main() -> int:
    nongear, _components = _nongear_preclass_weapon_damage()
    frontier, eligibility = _physical_frontier_with_witnesses()
    race_name, _race_delta = _race_ceiling()
    mundus_name = _weapon_damage_mundus_name()
    route = _pure_sorcerer_route()
    mastery = ExtremeClassMasteryPairService(DATABASE)
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=ExtremeOptimizationService(database_path=DATABASE),
        progression_service=ExtremeHypotheticalClassProgressionService(DATABASE),
    )

    expert = ExtremeSubclassSlotAllocationService.best_allocation(
        tuple(route.equipped_skill_lines),
        WEAPON_OBJECTIVE,
        reference_value=0.0,
    )
    if expert is None:
        raise RuntimeError("Pure Sorcerer has no reviewed Expert Mage slot allocation")
    expert_delta = float(expert.projected_delta)

    print("EXTREME WEAPON DAMAGE SORCERER EXPERT-MAGE SAME-BUILD FRONTIER")
    print(f"database={DATABASE}")
    print(f"weapon_damage_race={race_name!r}")
    print(f"weapon_damage_mundus={mundus_name!r}")
    print("pure_sorcerer=True")
    print(f"expert_mage_active_bar_delta={expert_delta:.3f}")
    print(f"expert_mage_slot_counts={expert.slot_counts!r}")
    print(f"expert_mage_sources={expert.reviewed_sources!r}")
    print("expert_mage_applied_before_class_mastery_percent=True")
    print()

    rows = []
    unresolved_all: list[str] = []
    neutralized_all: list[str] = []

    for gear, witness in frontier:
        preclass = float(nongear) + float(gear.weapon_damage)
        incumbent = _best_non_sorcerer(mastery, preclass)
        if incumbent is None or incumbent.projected_delta is None:
            unresolved_all.append(f"{gear.signature!r}: no reviewed non-Sorcerer incumbent")
            continue

        best_resource, resource_rows = _best_resource_for_witness(
            witness=witness,
            race_name=race_name,
            route=route,
            mundus_name=mundus_name,
            canonical=canonical,
        )
        if best_resource is None:
            unresolved_all.append(f"{gear.signature!r}: no canonical same-build resource score")
            continue

        (
            higher_resource,
            resource_objective,
            active_bar,
            provisioning,
            unresolved,
            neutralized,
            _payload,
        ) = best_resource
        unresolved_all.extend(str(item) for item in unresolved if str(item))
        neutralized_all.extend(str(item) for item in neutralized if str(item))
        for row in resource_rows:
            unresolved_all.extend(str(item) for item in row[4] if str(item))
            neutralized_all.extend(str(item) for item in row[5] if str(item))

        sorcerer_reference = preclass + expert_delta
        sorcerer = mastery.best_for_class(
            CharacterClass.SORCERER,
            WEAPON_OBJECTIVE,
            reference_value=sorcerer_reference,
            higher_max_resource=float(higher_resource),
        )
        if sorcerer is None or sorcerer.projected_delta is None:
            unresolved_all.append(f"{gear.signature!r}: Sorcerer Class Mastery score unavailable")
            continue

        incumbent_total = preclass + float(incumbent.projected_delta)
        sorcerer_total = sorcerer_reference + float(sorcerer.projected_delta)
        package = " + ".join(
            f"{name} {count}pc" for name, count in zip(gear.set_names, gear.counts)
        )
        rows.append(
            (
                sorcerer_total,
                package,
                preclass,
                expert_delta,
                float(higher_resource),
                str(resource_objective),
                str(active_bar),
                str(provisioning),
                float(sorcerer.percent),
                tuple(sorcerer.passive_names),
                incumbent.base_class.value,
                float(incumbent.projected_delta),
                tuple(incumbent.passive_names),
                incumbent_total,
                sorcerer_total > incumbent_total + 1e-9,
                tuple(unresolved),
            )
        )

    rows.sort(key=lambda row: (-row[0], row[1].casefold()))
    print("RESOLVED SAME-BUILD STATES WITH EXPERT MAGE")
    print(f"physical_pareto_count={len(frontier)}")
    print(f"rows_scored={len(rows)}")
    for row in rows:
        (
            sorcerer_total,
            package,
            preclass,
            expert_flat,
            higher_resource,
            resource_objective,
            active_bar,
            provisioning,
            sorcerer_percent,
            sorcerer_mastery,
            incumbent_class,
            incumbent_delta,
            incumbent_mastery,
            incumbent_total,
            wins,
            unresolved,
        ) = row
        print(f"  {package}")
        print(f"    preclass_weapon_damage={preclass:.3f}")
        print(f"    expert_mage_delta={expert_flat:.3f}")
        print(
            f"    canonical_higher_resource={higher_resource:.3f} objective={resource_objective} "
            f"active_bar={active_bar} provisioning={provisioning or '<none>'!r}"
        )
        print(
            f"    incumbent={incumbent_class} incumbent_delta={incumbent_delta:.3f} "
            f"incumbent_total={incumbent_total:.3f} mastery={incumbent_mastery!r}"
        )
        print(
            f"    sorcerer_mastery_delta={sorcerer_total - preclass - expert_flat:.3f} "
            f"sorcerer_percent={sorcerer_percent:.3f} mastery={sorcerer_mastery!r}"
        )
        print(f"    sorcerer_total_weapon_damage={sorcerer_total:.3f}")
        print(f"    sorcerer_beats_incumbent={wins}")
        print(f"    unresolved_count={len(unresolved)}")
        print()

    clean_unresolved = tuple(dict.fromkeys(message for message in unresolved_all if message))
    clean_neutralized = tuple(dict.fromkeys(message for message in neutralized_all if message))
    clean_rows = tuple(row for row in rows if not row[-1])
    winners = tuple(row for row in clean_rows if row[-2])
    best = winners[0] if winners else None

    print("FRONTIER SUMMARY")
    print(f"clean_same_build_rows={len(clean_rows)}")
    print(f"sorcerer_winning_resolved_states={len(winners)}")
    if best is not None:
        print(f"best_resolved_sorcerer_package={best[1]!r}")
        print(f"best_resolved_sorcerer_higher_resource={best[4]:.3f}")
        print(f"best_resolved_sorcerer_expert_mage_delta={best[3]:.3f}")
        print(f"best_resolved_sorcerer_percent={best[8]:.3f}")
        print(f"best_resolved_sorcerer_weapon_damage={best[0]:.3f}")
    print(f"slot_eligibility_unresolved={len(eligibility.unresolved)}")
    print(f"same_build_resource_unresolved_count={len(clean_unresolved)}")
    for message in clean_unresolved[:10]:
        print(f"  unresolved: {message}")
    print(f"neutralized_armor_metadata_warning_count={len(clean_neutralized)}")
    print(f"resolved_class_frontier_incumbent_ready={bool(best is not None and not clean_unresolved and not eligibility.unresolved)}")
    print("final_weapon_damage_record_closed=False")
    print(
        "NEXT_STEP=use the corrected resolved Sorcerer incumbent as the hurdle for the retained unresolved named-set "
        "Weapon Damage mechanics; resolve or proof-bound those set effects once at the semantic breakpoint layer, "
        "then rerun physical realization instead of reviewing thousands of combinations individually"
    )
    return 0 if best is not None and not clean_unresolved and not eligibility.unresolved else 2


if __name__ == "__main__":
    raise SystemExit(main())
