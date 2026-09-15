from __future__ import annotations

"""Rebuild the Extreme Weapon Damage hurdle with the canonical potion-active baseline.

The Extreme blueprint already defines Weapon Power potion -> Major Brutality for the
weapon_damage objective.  Earlier frontier audits compared unresolved gear challengers
against a resting resolved incumbent, which accidentally allowed Dreugh King Slayer's
Major Brutality to look like a unique gear advantage.

This audit fixes that boundary without changing any database state:

* Major Brutality (+20% Weapon Damage) is present on every candidate through the
  self-usable Weapon Power potion baseline.
* The resolved incumbent is recomputed from the same mechanic-complete physical gear
  frontier with Expert Mage and canonical same-build Max Resource.
* Dreugh King Slayer retains only its universal static Weapon/Spell Damage because its
  Major Brutality duplicates the baseline named buff.
* Ability-scoped set corrections from the preceding audit remain in force.
* Any remaining gear percentage ceiling is still compounded separately as a favorable
  overbound, so pruning remains proof-safe.

This is still a dominance audit.  Conditional generic power such as Kvatch Gladiator,
Burning Spellweave, and Armor of Truth remains favorable until its exact runtime state
is reviewed.
"""

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.character_build.character_class import CharacterClass
from minmax.gear_set_repository import GearSetRepository
from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from services.extreme_class_mastery_pair_service import ExtremeClassMasteryPairService
from services.extreme_hypothetical_class_progression_service import (
    ExtremeHypotheticalClassProgressionService,
)
from services.extreme_named_gear_canonical_stat_evaluator import (
    ExtremeNamedGearCanonicalStatEvaluator,
)
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationService,
)
from services.extreme_optimization_service import ExtremeOptimizationService
from services.extreme_structural_core_stat_record_service import (
    ExtremeCanonicalStructuralStatEvaluator,
)
from services.extreme_twice_born_mundus_structural_stat_evaluator import (
    ExtremeTwiceBornMundusStructuralStatEvaluator,
)
from services.extreme_subclass_slot_allocation_service import (
    ExtremeSubclassSlotAllocationService,
)

import tools.audit_extreme_weapon_damage_ability_scoped_set_tightening as scoped
import tools.audit_extreme_weapon_damage_same_build_resource_tightening as tightening
from tools.audit_extreme_weapon_damage_joint_named_gear_frontier import _joint_rows
from tools.audit_extreme_weapon_damage_joint_named_gear_realization import (
    _filtered_breakpoints,
    _filtered_eligibility,
    _filtered_topologies,
)
from tools.audit_extreme_weapon_damage_physical_gear_resource_requirements import (
    _nongear_preclass_weapon_damage,
)
from tools.audit_extreme_weapon_damage_preweapon_upper_bound import _race_ceiling
from tools.audit_extreme_weapon_damage_sorcerer_free_resource_witness import (
    _pure_sorcerer_route,
    _weapon_damage_mundus_name,
)
from tools.audit_extreme_weapon_damage_sorcerer_named_gear_same_build import (
    DATABASE,
    EMPEROR_BUFF,
    RESOURCE_OBJECTIVES,
    _physical_frontier_with_witnesses,
    _provisioning_candidates,
    _reconcile_resource_unresolved,
    _resource_candidate,
)

OBJECTIVE = "weapon_damage"
MAJOR_BRUTALITY_PERCENT = 0.20
DREUGH_KING_SLAYER = "Dreugh King Slayer"
TWICE_BORN_STAR = "Twice-Born Star"


@dataclass(frozen=True)
class _Row:
    package: str
    flat_bound: float
    gear_percent_bound: float
    higher_resource: float
    resource_objective: str
    provisioning: str
    mastery_percent: float
    total: float
    twice_born: bool
    unresolved: tuple[str, ...]


def _expert_mage_delta(route) -> float:
    result = ExtremeSubclassSlotAllocationService.best_allocation(
        tuple(route.equipped_skill_lines),
        OBJECTIVE,
        reference_value=0.0,
    )
    if result is None:
        raise RuntimeError("Pure Sorcerer Expert Mage allocation unavailable")
    return float(result.projected_delta)


def _resource_rows_for_evaluator(
    evaluator,
    *,
    race_name: str,
    route,
    ordinary_mundus: str | None,
):
    rows = []
    for objective in RESOURCE_OBJECTIVES:
        for active_bar in ("front", "back"):
            candidate = _resource_candidate(
                objective_key=objective,
                active_bar=active_bar,
                race_name=race_name,
                route=route,
            )
            for provisioning in _provisioning_candidates(objective):
                kwargs = {
                    "food": provisioning,
                    "active_buffs": (EMPEROR_BUFF,),
                }
                if ordinary_mundus is not None:
                    kwargs["mundus"] = ordinary_mundus
                value, payload, unresolved = evaluator.evaluate_candidate(
                    objective,
                    candidate,
                    **kwargs,
                )
                effective, neutralized = scoped.key_tightening._reconcile_resource_unresolved(
                    objective,
                    tuple(unresolved),
                )
                rows.append(
                    (
                        float(value),
                        objective,
                        active_bar,
                        provisioning,
                        effective,
                        neutralized,
                        payload,
                    )
                )
    return tuple(rows)


def _best_resource(rows):
    if not rows:
        return None
    return min(
        rows,
        key=lambda row: (
            len(row[4]),
            -row[0],
            row[1],
            row[2],
            row[3],
        ),
    )


def _resolved_incumbent(
    *,
    canonical,
    mastery,
    race_name: str,
    route,
    mundus_name: str,
    nongear: float,
    expert_mage: float,
):
    frontier, eligibility = _physical_frontier_with_witnesses()
    rows = []
    unresolved_all = []
    for gear, witness in frontier:
        named = ExtremeNamedGearCanonicalStatEvaluator(
            evaluator=canonical,
            realization=witness,
        )
        resource_rows = _resource_rows_for_evaluator(
            named,
            race_name=race_name,
            route=route,
            ordinary_mundus=mundus_name,
        )
        best = _best_resource(resource_rows)
        if best is None:
            unresolved_all.append(f"{gear.signature!r}: no resource score")
            continue
        higher_resource, objective, _bar, provisioning, unresolved, _neutralized, _payload = best
        unresolved_all.extend(str(item) for item in unresolved if str(item))
        reference = float(nongear) + float(gear.weapon_damage) + float(expert_mage)
        sorcerer = mastery.best_for_class(
            CharacterClass.SORCERER,
            OBJECTIVE,
            reference_value=reference,
            higher_max_resource=float(higher_resource),
        )
        if sorcerer is None:
            unresolved_all.append(f"{gear.signature!r}: Sorcerer mastery unavailable")
            continue
        total = reference * (1.0 + float(sorcerer.percent) + MAJOR_BRUTALITY_PERCENT)
        package = " + ".join(
            f"{name} {count}pc" for name, count in zip(gear.set_names, gear.counts)
        )
        rows.append(
            (
                float(total),
                package,
                float(reference),
                float(higher_resource),
                str(objective),
                str(provisioning),
                float(sorcerer.percent),
                tuple(unresolved),
            )
        )
    rows.sort(key=lambda row: (-row[0], row[1].casefold()))
    clean = tuple(row for row in rows if not row[-1])
    if not clean:
        raise RuntimeError("No clean resolved potion-active incumbent")
    unresolved_unique = tuple(dict.fromkeys(item for item in unresolved_all if item))
    return clean[0], eligibility, unresolved_unique


def _bounded_frontier(repository: GearSetRepository):
    original_breakpoints, catalogs, joint_rows = _joint_rows(repository)
    weapon_map = {
        (int(row.set_id), int(row.piece_count)): row
        for row in catalogs[OBJECTIVE].evidence
    }
    bounded = []
    for joint in joint_rows:
        if not joint.unresolved and not joint.has_positive_joint_value:
            continue
        evidence = weapon_map.get((int(joint.set_id), int(joint.piece_count)))
        if evidence is None:
            continue
        bound = scoped._semantic_bound(joint, evidence)
        if str(joint.set_name) == DREUGH_KING_SLAYER and int(joint.piece_count) == 5:
            bound = scoped.reduced._BoundedBreakpoint(
                row=joint,
                flat=float(bound.flat),
                percent=0.0,
                exact_execution_required=bool(bound.exact_execution_required),
                assumptions=tuple(bound.assumptions) + (
                    "Major Brutality duplicates Weapon Power potion baseline",
                ),
            )
        bounded.append(bound)
    reduced_rows = scoped.reduced._semantic_pareto(tuple(bounded))
    reduced_joint = scoped.reduced._joint_row_map(reduced_rows)
    breakpoints = _filtered_breakpoints(original_breakpoints, reduced_joint)
    eligibility = _filtered_eligibility(reduced_joint)
    topologies = _filtered_topologies(repository, breakpoints)
    return reduced_rows, breakpoints, eligibility, topologies


def main() -> int:
    repository = GearSetRepository(DATABASE)
    race_name, _race_delta = _race_ceiling()
    mundus_name = _weapon_damage_mundus_name()
    route = _pure_sorcerer_route()
    nongear, _components = _nongear_preclass_weapon_damage()
    expert_mage = _expert_mage_delta(route)
    mastery = ExtremeClassMasteryPairService(DATABASE)
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=ExtremeOptimizationService(database_path=DATABASE),
        progression_service=ExtremeHypotheticalClassProgressionService(DATABASE),
    )
    mundus_repository = MundusRepository(DATABASE, game_update=U50_GAME_UPDATE)

    incumbent, resolved_eligibility, resolved_unresolved = _resolved_incumbent(
        canonical=canonical,
        mastery=mastery,
        race_name=race_name,
        route=route,
        mundus_name=mundus_name,
        nongear=nongear,
        expert_mage=expert_mage,
    )
    (
        incumbent_total,
        incumbent_package,
        incumbent_reference,
        incumbent_resource,
        incumbent_resource_objective,
        incumbent_provisioning,
        incumbent_mastery_percent,
        _incumbent_unresolved,
    ) = incumbent

    reduced_rows, breakpoints, eligibility, topologies = _bounded_frontier(repository)
    bounded_by_key = {row.key: row for row in reduced_rows}
    realization_service = ExtremeNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
    )

    output: list[_Row] = []
    resource_unresolved = []
    physical_realizations = 0
    for topology in topologies.topologies:
        result = realization_service.realize_topology(topology)
        for witness in result.realizations:
            physical_realizations += 1
            flat = 0.0
            gear_percent = 0.0
            twice_born = False
            for set_id, count, set_name in zip(witness.set_ids, witness.counts, witness.set_names):
                bound = bounded_by_key.get((int(set_id), int(count)))
                if bound is None:
                    raise RuntimeError(f"Missing bound for {(set_id, count)!r}")
                flat += float(bound.flat)
                gear_percent += float(bound.percent)
                twice_born = twice_born or (
                    str(set_name) == TWICE_BORN_STAR and int(count) == 5
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
            package = " + ".join(
                f"{name} {count}pc" for name, count in zip(witness.set_names, witness.counts)
            )
            if best is None:
                resource_unresolved.append(f"{package}: no resource score")
                continue
            higher_resource, objective, _bar, provisioning, unresolved, _neutralized, _payload = best
            resource_unresolved.extend(str(item) for item in unresolved if str(item))
            reference = float(nongear) + float(flat) + float(expert_mage)
            sorcerer = mastery.best_for_class(
                CharacterClass.SORCERER,
                OBJECTIVE,
                reference_value=reference,
                higher_max_resource=float(higher_resource),
            )
            if sorcerer is None:
                resource_unresolved.append(f"{package}: Sorcerer mastery unavailable")
                continue

            baseline_total = reference * (
                1.0 + float(sorcerer.percent) + MAJOR_BRUTALITY_PERCENT
            )
            optimistic = baseline_total * (1.0 + float(gear_percent))
            output.append(
                _Row(
                    package=package,
                    flat_bound=float(flat),
                    gear_percent_bound=float(gear_percent),
                    higher_resource=float(higher_resource),
                    resource_objective=str(objective),
                    provisioning=str(provisioning),
                    mastery_percent=float(sorcerer.percent),
                    total=float(optimistic),
                    twice_born=twice_born,
                    unresolved=tuple(unresolved),
                )
            )

    clean = tuple(row for row in output if not row.unresolved)
    pruned = tuple(row for row in clean if row.total <= incumbent_total + 1e-9)
    survivors = tuple(
        sorted(
            (row for row in clean if row.total > incumbent_total + 1e-9),
            key=lambda row: (-row.total, row.package.casefold()),
        )
    )
    unresolved_unique = tuple(dict.fromkeys(item for item in resource_unresolved if item))

    print("EXTREME WEAPON DAMAGE MAJOR BRUTALITY BASELINE")
    print(f"database={DATABASE}")
    print("weapon_power_potion_baseline=True")
    print(f"major_brutality_percent={MAJOR_BRUTALITY_PERCENT:.6f}")
    print("major_brutality_percent_bucket_additive_with_class_mastery=True")
    print("dreugh_major_brutality_duplicate=True")
    print(f"expert_mage_delta={expert_mage:.3f}")
    print(f"nongear_preclass_weapon_damage={nongear:.3f}")
    print()

    print("POTION-ACTIVE RESOLVED INCUMBENT")
    print(f"package={incumbent_package!r}")
    print(f"pre_percent_reference={incumbent_reference:.3f}")
    print(f"higher_resource={incumbent_resource:.3f}")
    print(f"resource_objective={incumbent_resource_objective}")
    print(f"provisioning={incumbent_provisioning!r}")
    print(f"font_plus_defense_percent={incumbent_mastery_percent:.6f}")
    print(f"major_brutality_percent={MAJOR_BRUTALITY_PERCENT:.6f}")
    print(f"resolved_incumbent_weapon_damage={incumbent_total:.3f}")
    print()

    print("CHALLENGER REDUCTION")
    print(f"semantic_pareto_breakpoints={len(reduced_rows)}")
    print(f"candidate_topologies={len(topologies.topologies)}")
    print(f"physical_realizations={physical_realizations}")
    print(f"clean_same_build_rows={len(clean)}")
    print(f"states_pruned_below_potion_active_incumbent={len(pruned)}")
    print(f"states_still_above_potion_active_incumbent={len(survivors)}")
    print(f"ordinary_survivors={sum(1 for row in survivors if not row.twice_born)}")
    print(f"twice_born_survivors={sum(1 for row in survivors if row.twice_born)}")
    print()

    print("SURVIVORS")
    for row in survivors:
        print(
            f"  {row.package} | flat_bound={row.flat_bound:.3f} "
            f"gear_percent_bound={row.gear_percent_bound:.6f} "
            f"higher_resource={row.higher_resource:.3f} "
            f"resource_objective={row.resource_objective} "
            f"provisioning={row.provisioning or '<none>'!r} "
            f"font_plus_defense_percent={row.mastery_percent:.6f} "
            f"optimistic_final={row.total:.3f} twice_born={row.twice_born}"
        )
    print()

    ready = (
        bool(clean)
        and not eligibility.unresolved
        and not resolved_eligibility.unresolved
        and not unresolved_unique
        and not resolved_unresolved
    )
    print("PROOF STATUS")
    print(f"resource_unresolved_count={len(unresolved_unique)}")
    print(f"resolved_frontier_unresolved_count={len(resolved_unresolved)}")
    print(f"major_brutality_baseline_ready={ready}")
    print("final_weapon_damage_record_closed=False")
    print(
        "NEXT_STEP=review only the surviving generic conditional named-set power mechanics against the potion-active incumbent; ability-scoped bonuses and duplicate Major Brutality are already excluded from the Weapon Damage record"
    )
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
