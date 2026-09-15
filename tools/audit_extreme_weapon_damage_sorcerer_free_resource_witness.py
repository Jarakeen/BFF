from __future__ import annotations

"""Construct a Weapon-Damage-preserving lower bound for Sorcerer higher Max Resource.

The physical-gear threshold audit proved that the cheapest reviewed Sorcerer route
needs 49,066 non-gear higher Max Resource. This audit does not independently maximize
resource axes that conflict with the Weapon Damage subtotal. It preserves the reviewed
Weapon Damage race and Mundus winner, fixes pure Sorcerer, and uses only axes that do
not reduce the reviewed Weapon Damage subtotal: all 64 attributes into one resource,
a legal provisioning witness, active Emperor with six Home Keeps, and either active
bar. Armor glyphs, resource jewelry, resource CP, and named gear are deliberately
omitted, so the resulting resource score is a constructive lower bound.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.character_build.character_class import CharacterClass
from minmax.character_progression import AttributeAllocation
from minmax.combat_state import EMPEROR_STATE_MARKER_PREFIX
from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from services.extreme_armor_mundus_joint_objective_service import (
    ExtremeArmorMundusJointObjectiveService,
)
from services.extreme_heal_class_route_service import ExtremeHealClassRouteService
from services.extreme_hypothetical_class_progression_service import (
    ExtremeHypotheticalClassProgressionService,
)
from services.extreme_optimization_service import ExtremeOptimizationService
from services.extreme_resource_provisioning_projection_service import (
    ExtremeResourceProvisioningProjectionService,
)
from services.extreme_structural_core_stat_record_service import (
    ExtremeCanonicalStructuralStatEvaluator,
)
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate
from services.extreme_class_mastery_pair_service import ExtremeClassMasteryPairService
from tools.audit_extreme_weapon_damage_physical_gear_resource_requirements import (
    _best_non_sorcerer,
    _minimum_total_resource,
    _nongear_preclass_weapon_damage,
    _physical_frontier,
)
from tools.audit_extreme_weapon_damage_preweapon_upper_bound import _race_ceiling

DATABASE = ROOT / "data" / "eso.db"
WEAPON_OBJECTIVE = "weapon_damage"
RESOURCE_OBJECTIVES = ("max_magicka", "max_stamina")
EMPEROR_BUFF = f"{EMPEROR_STATE_MARKER_PREFIX}6"


def _pure_sorcerer_route():
    routes = ExtremeHealClassRouteService().routes_for_base_class(CharacterClass.SORCERER)
    pure = tuple(route for route in routes if not route.is_subclassed)
    if len(pure) != 1:
        raise RuntimeError(f"Expected one pure Sorcerer route, found {len(pure)}")
    return pure[0]


def _weapon_damage_mundus_name() -> str:
    row = ExtremeArmorMundusJointObjectiveService.best_for_objective(
        MundusRepository(DATABASE, game_update=U50_GAME_UPDATE),
        WEAPON_OBJECTIVE,
        reference_value=0.0,
    )
    if row is None:
        raise RuntimeError("No canonical Weapon Damage armor/Mundus winner")
    return str(row.mundus_name)


def _provisioning_candidates(objective_key: str) -> tuple[str, ...]:
    projection = ExtremeResourceProvisioningProjectionService(
        ProvisioningStaticRepository(DATABASE)
    ).build(objective_key)
    rows = [""]
    if projection.food_witness:
        rows.append(str(projection.food_witness))
    if projection.drink_witness:
        rows.append(str(projection.drink_witness))
    return tuple(dict.fromkeys(rows))


def _minimum_required_non_gear_resource() -> tuple[float, str]:
    nongear, _components = _nongear_preclass_weapon_damage()
    frontier, _eligibility = _physical_frontier()
    mastery = ExtremeClassMasteryPairService(DATABASE)
    best = None
    best_package = ""
    for gear in frontier:
        reference = nongear + float(gear.weapon_damage)
        incumbent = _best_non_sorcerer(mastery, reference)
        if incumbent is None or incumbent.projected_delta is None:
            continue
        threshold, _sorc = _minimum_total_resource(
            mastery,
            reference,
            float(incumbent.projected_delta),
        )
        if threshold is None:
            continue
        required = max(0.0, float(threshold) - float(gear.higher_resource))
        package = " + ".join(
            f"{name} {count}pc" for name, count in zip(gear.set_names, gear.counts)
        )
        if best is None or required < best - 1e-9:
            best = required
            best_package = package
    if best is None:
        raise RuntimeError("No finite Sorcerer non-gear resource requirement")
    return float(best), best_package


def main() -> int:
    race_name, _race_delta = _race_ceiling()
    mundus_name = _weapon_damage_mundus_name()
    route = _pure_sorcerer_route()
    evaluator = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=ExtremeOptimizationService(database_path=DATABASE),
        progression_service=ExtremeHypotheticalClassProgressionService(DATABASE),
    )
    required, threshold_package = _minimum_required_non_gear_resource()

    print("EXTREME WEAPON DAMAGE SORCERER FREE-RESOURCE WITNESS")
    print(f"database={DATABASE}")
    print(f"weapon_damage_race={race_name!r}")
    print(f"weapon_damage_mundus={mundus_name!r}")
    print("pure_sorcerer=True")
    print(f"emperor_runtime_marker={EMPEROR_BUFF!r}")
    print(f"minimum_required_non_gear_higher_resource={required:.3f}")
    print(f"threshold_package={threshold_package!r}")
    print("resource_jewelry_in_scope=False")
    print("resource_cp_in_scope=False")
    print("armor_resource_glyphs_in_scope=False")
    print("named_gear_resource_in_scope=False")
    print("result_is_constructive_lower_bound=True")
    print()

    best = None
    rows = []
    for objective in RESOURCE_OBJECTIVES:
        attributes = (
            AttributeAllocation(health=0, magicka=64, stamina=0)
            if objective == "max_magicka"
            else AttributeAllocation(health=0, magicka=0, stamina=64)
        )
        for active_bar in ("front", "back"):
            candidate = ExtremeStructuralCandidate(
                race=race_name,
                class_route=route,
                attributes=attributes,
                active_bar=active_bar,
            )
            for provisioning in _provisioning_candidates(objective):
                value, payload, unresolved = evaluator.evaluate_candidate(
                    objective,
                    candidate,
                    mundus=mundus_name,
                    food=provisioning,
                    active_buffs=(EMPEROR_BUFF,),
                )
                row = (
                    float(value),
                    objective,
                    active_bar,
                    provisioning,
                    tuple(unresolved),
                    payload,
                )
                rows.append(row)
                if best is None or row[0] > best[0] + 1e-9:
                    best = row

    rows.sort(key=lambda row: (-row[0], row[1], row[2], row[3]))
    print("CONSTRUCTIVE RESOURCE CANDIDATES")
    for value, objective, active_bar, provisioning, unresolved, _payload in rows:
        print(
            f"  objective={objective} active_bar={active_bar} "
            f"provisioning={provisioning or '<none>'!r} value={value:.3f} "
            f"unresolved={len(unresolved)}"
        )
        for message in unresolved[:3]:
            print(f"    unresolved: {message}")
    print()

    if best is None:
        print("constructive_higher_resource=<none>")
        print("sorcerer_threshold_cleared=False")
        return 2

    value, objective, active_bar, provisioning, unresolved, _payload = best
    cleared = bool(not unresolved and value >= required - 1e-9)
    print("BEST CONSTRUCTIVE WITNESS")
    print(f"higher_resource={value:.3f}")
    print(f"resource_objective={objective}")
    print(f"active_bar={active_bar}")
    print(f"provisioning={provisioning or '<none>'!r}")
    print(f"unresolved_count={len(unresolved)}")
    print(f"threshold_headroom={value - required:.3f}")
    print(f"sorcerer_threshold_cleared={cleared}")
    print("final_weapon_damage_class_route_closed=False")
    print("final_weapon_damage_record_closed=False")
    print(
        "NEXT_STEP=if this conservative same-build witness clears the cheapest threshold, "
        "keep Sorcerer as a live class winner and optimize only the threshold-crossing physical "
        "gear packages with the remaining Weapon-Damage-preserving armor/CP/runtime axes; if it "
        "does not clear, add the omitted non-conflicting resource axes before attempting any prune"
    )
    return 0 if cleared else 2


if __name__ == "__main__":
    raise SystemExit(main())
