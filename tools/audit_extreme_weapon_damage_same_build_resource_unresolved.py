from __future__ import annotations

"""Expose the single unresolved same-build resource witness from the tightening audit."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from services.extreme_hypothetical_class_progression_service import ExtremeHypotheticalClassProgressionService
from services.extreme_named_gear_canonical_stat_evaluator import ExtremeNamedGearCanonicalStatEvaluator
from services.extreme_named_gear_set_catalog_realization_service import ExtremeNamedGearSetCatalogRealizationService
from services.extreme_optimization_service import ExtremeOptimizationService
from services.extreme_structural_core_stat_record_service import ExtremeCanonicalStructuralStatEvaluator
from services.extreme_twice_born_mundus_structural_stat_evaluator import ExtremeTwiceBornMundusStructuralStatEvaluator
from tools.audit_extreme_weapon_damage_reduced_physical_upper_bound import DATABASE, TWICE_BORN_STAR
from tools.audit_extreme_weapon_damage_same_build_resource_tightening import (
    _best_resource,
    _bounded_frontier,
    _resource_rows_for_evaluator,
)
from tools.audit_extreme_weapon_damage_sorcerer_named_gear_same_build import (
    _pure_sorcerer_route,
    _weapon_damage_mundus_name,
)
from tools.audit_extreme_weapon_damage_preweapon_upper_bound import _race_ceiling


def main() -> int:
    repository = GearSetRepository(DATABASE)
    reduced, breakpoints, eligibility, topologies = _bounded_frontier(repository)
    realization_service = ExtremeNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
    )

    race_name, _ = _race_ceiling()
    mundus_name = _weapon_damage_mundus_name()
    route = _pure_sorcerer_route()
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=ExtremeOptimizationService(database_path=DATABASE),
        progression_service=ExtremeHypotheticalClassProgressionService(DATABASE),
    )
    mundus_repository = MundusRepository(DATABASE, game_update=U50_GAME_UPDATE)

    unresolved_rows = []
    total = 0
    for topology in topologies.topologies:
        result = realization_service.realize_topology(topology)
        for witness in result.realizations:
            total += 1
            package = " + ".join(
                f"{name} {count}pc" for name, count in zip(witness.set_names, witness.counts)
            )
            twice_born = any(
                str(name) == TWICE_BORN_STAR and int(count) == 5
                for name, count in zip(witness.set_names, witness.counts)
            )
            named = ExtremeNamedGearCanonicalStatEvaluator(
                evaluator=canonical,
                realization=witness,
            )
            if twice_born:
                evaluator = ExtremeTwiceBornMundusStructuralStatEvaluator(
                    evaluator=named,
                    mundus_repository=mundus_repository,
                )
                resource_rows = _resource_rows_for_evaluator(
                    evaluator,
                    race_name=race_name,
                    route=route,
                    ordinary_mundus=None,
                )
            else:
                resource_rows = _resource_rows_for_evaluator(
                    named,
                    race_name=race_name,
                    route=route,
                    ordinary_mundus=mundus_name,
                )

            best = _best_resource(resource_rows)
            if best is None:
                unresolved_rows.append((package, "<no best resource row>"))
                continue
            value, objective, active_bar, provisioning, unresolved, neutralized, payload = best
            for message in unresolved:
                unresolved_rows.append(
                    (
                        package,
                        str(message),
                        float(value),
                        str(objective),
                        str(active_bar),
                        str(provisioning),
                        twice_born,
                        tuple(neutralized),
                    )
                )

    print("EXTREME WEAPON DAMAGE SAME-BUILD RESOURCE UNRESOLVED WITNESS")
    print(f"database={DATABASE}")
    print(f"physical_realizations={total}")
    print(f"unresolved_witness_message_count={len(unresolved_rows)}")
    print()
    for row in unresolved_rows:
        print(f"package={row[0]!r}")
        print(f"unresolved={row[1]!r}")
        if len(row) > 2:
            print(f"resource_value={row[2]:.3f}")
            print(f"resource_objective={row[3]}")
            print(f"active_bar={row[4]}")
            print(f"provisioning={row[5]!r}")
            print(f"twice_born={row[6]}")
            print(f"neutralized={row[7]!r}")
        print()

    print(f"resource_unresolved_exposed={bool(unresolved_rows)}")
    print("final_weapon_damage_record_closed=False")
    print("NEXT_STEP=classify the printed unresolved message as mechanical or metadata-only before changing the tightening proof gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
