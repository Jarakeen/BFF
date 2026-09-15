from __future__ import annotations

"""Tighten reduced Weapon Damage challengers with canonical same-build resources.

The preceding reduced physical audit intentionally used the global 108,319 higher-
resource ceiling for every witness. That is proof-safe but far too generous. This
stage keeps each gear power contribution at its existing favorable semantic upper
bound, while replacing the independent resource ceiling with the Max Magicka / Max
Stamina actually available to that same physical gear witness under the reviewed
Weapon-Damage-preserving Sorcerer state.

Ordinary witnesses retain The Warrior. Twice-Born Star witnesses execute the existing
finite two-Mundus search, so a resource boon can coexist with The Warrior only when the
canonical executor proves that exact state legal.

This remains a dominance audit, not final executable proc scoring. Conditional named-
set power ceilings are still deliberately overcredited. A row below the incumbent here
is therefore permanently pruned; a surviving row merely requires exact set-mechanic
execution or a stronger final bound.
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
from tools.audit_extreme_weapon_damage_reduced_physical_upper_bound import (
    DATABASE,
    OBJECTIVE,
    RESOLVED_INCUMBENT,
    TWICE_BORN_STAR,
    _expert_mage_delta,
    _joint_row_map,
    _semantic_bound,
    _semantic_pareto,
    _weapon_evidence_map,
)
from tools.audit_extreme_weapon_damage_joint_named_gear_frontier import _joint_rows
from tools.audit_extreme_weapon_damage_joint_named_gear_realization import (
    _filtered_breakpoints,
    _filtered_eligibility,
    _filtered_topologies,
)
from tools.audit_extreme_weapon_damage_physical_gear_resource_requirements import (
    _nongear_preclass_weapon_damage,
)
from tools.audit_extreme_weapon_damage_sorcerer_named_gear_same_build import (
    EMPEROR_BUFF,
    RESOURCE_OBJECTIVES,
    _provisioning_candidates,
    _pure_sorcerer_route,
    _reconcile_resource_unresolved,
    _resource_candidate,
    _weapon_damage_mundus_name,
)
from tools.audit_extreme_weapon_damage_preweapon_upper_bound import _race_ceiling


@dataclass(frozen=True)
class _TightenedRow:
    package: str
    set_names: tuple[str, ...]
    set_ids: tuple[int, ...]
    counts: tuple[int, ...]
    flat_bound: float
    percent_bound: float
    higher_resource: float
    resource_objective: str
    provisioning: str
    mastery_percent: float
    optimistic_final: float
    twice_born: bool
    unresolved: tuple[str, ...]

    @property
    def signature(self) -> tuple:
        return (self.set_ids, self.counts)


def _bounded_frontier(repository: GearSetRepository):
    original_breakpoints, catalogs, joint_rows = _joint_rows(repository)
    weapon_map = _weapon_evidence_map(catalogs)
    bounded = []
    for joint in joint_rows:
        if not joint.unresolved and not joint.has_positive_joint_value:
            continue
        evidence = weapon_map.get((int(joint.set_id), int(joint.piece_count)))
        if evidence is None:
            continue
        bounded.append(_semantic_bound(joint, evidence))
    reduced = _semantic_pareto(tuple(bounded))
    reduced_joint = _joint_row_map(reduced)
    breakpoints = _filtered_breakpoints(original_breakpoints, reduced_joint)
    eligibility = _filtered_eligibility(reduced_joint)
    topologies = _filtered_topologies(repository, breakpoints)
    return reduced, breakpoints, eligibility, topologies


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
                effective, neutralized = _reconcile_resource_unresolved(
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


def main() -> int:
    repository = GearSetRepository(DATABASE)
    reduced, breakpoints, eligibility, topologies = _bounded_frontier(repository)
    bounded_by_key = {row.key: row for row in reduced}
    realization_service = ExtremeNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
    )

    race_name, _race_delta = _race_ceiling()
    mundus_name = _weapon_damage_mundus_name()
    route = _pure_sorcerer_route()
    nongear, _components = _nongear_preclass_weapon_damage()
    expert_mage = _expert_mage_delta()
    mastery = ExtremeClassMasteryPairService(DATABASE)
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=ExtremeOptimizationService(database_path=DATABASE),
        progression_service=ExtremeHypotheticalClassProgressionService(DATABASE),
    )
    mundus_repository = MundusRepository(DATABASE, game_update=U50_GAME_UPDATE)

    rows: list[_TightenedRow] = []
    resource_unresolved: list[str] = []
    neutralized: list[str] = []
    physical_realizations = 0

    for topology in topologies.topologies:
        result = realization_service.realize_topology(topology)
        for witness in result.realizations:
            physical_realizations += 1
            flat = 0.0
            percent = 0.0
            twice_born = False
            for set_id, count, set_name in zip(witness.set_ids, witness.counts, witness.set_names):
                bound = bounded_by_key.get((int(set_id), int(count)))
                if bound is None:
                    raise RuntimeError(
                        f"Missing reduced semantic bound for {(set_id, count)!r}"
                    )
                flat += float(bound.flat)
                percent += float(bound.percent)
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
                f"{name} {count}pc"
                for name, count in zip(witness.set_names, witness.counts)
            )
            if best is None:
                resource_unresolved.append(f"{package}: no resource score")
                continue

            higher_resource, objective, _bar, provisioning, unresolved, row_neutralized, _payload = best
            resource_unresolved.extend(str(item) for item in unresolved if str(item))
            neutralized.extend(str(item) for item in row_neutralized if str(item))

            sorcerer = mastery.best_for_class(
                CharacterClass.SORCERER,
                OBJECTIVE,
                reference_value=float(nongear) + float(flat) + float(expert_mage),
                higher_max_resource=float(higher_resource),
            )
            if sorcerer is None or sorcerer.projected_delta is None:
                resource_unresolved.append(f"{package}: Sorcerer mastery score unavailable")
                continue

            base = float(nongear) + float(flat) + float(expert_mage)
            mastery_percent = float(sorcerer.percent)
            # Preserve the prior proof-safe convention: gear percentage is compounded
            # separately, which can only make the challenger more favorable.
            optimistic = base * (1.0 + mastery_percent) * (1.0 + float(percent))
            rows.append(
                _TightenedRow(
                    package=package,
                    set_names=tuple(str(value) for value in witness.set_names),
                    set_ids=tuple(int(value) for value in witness.set_ids),
                    counts=tuple(int(value) for value in witness.counts),
                    flat_bound=float(flat),
                    percent_bound=float(percent),
                    higher_resource=float(higher_resource),
                    resource_objective=str(objective),
                    provisioning=str(provisioning),
                    mastery_percent=mastery_percent,
                    optimistic_final=float(optimistic),
                    twice_born=twice_born,
                    unresolved=tuple(unresolved),
                )
            )

    clean = tuple(row for row in rows if not row.unresolved)
    pruned = tuple(row for row in clean if row.optimistic_final <= RESOLVED_INCUMBENT + 1e-9)
    survivors = tuple(
        sorted(
            (row for row in clean if row.optimistic_final > RESOLVED_INCUMBENT + 1e-9),
            key=lambda row: (-row.optimistic_final, row.signature),
        )
    )
    ordinary_survivors = tuple(row for row in survivors if not row.twice_born)
    tbs_survivors = tuple(row for row in survivors if row.twice_born)
    unresolved_unique = tuple(dict.fromkeys(item for item in resource_unresolved if item))
    neutralized_unique = tuple(dict.fromkeys(item for item in neutralized if item))

    print("EXTREME WEAPON DAMAGE SAME-BUILD RESOURCE TIGHTENING")
    print(f"database={DATABASE}")
    print(f"resolved_same_build_incumbent={RESOLVED_INCUMBENT:.3f}")
    print(f"weapon_damage_race={race_name!r}")
    print(f"ordinary_mundus={mundus_name!r}")
    print("pure_sorcerer=True")
    print(f"expert_mage_delta={expert_mage:.3f}")
    print(f"nongear_preclass_weapon_damage={nongear:.3f}")
    print("conditional_gear_power_still_upper_bounded=True")
    print("same_build_resource_canonical=True")
    print("twice_born_two_mundus_exact_resource_search=True")
    print()

    print("REDUCED PHYSICAL INPUT")
    print(f"semantic_pareto_breakpoints={len(reduced)}")
    print(f"candidate_topologies={len(topologies.topologies)}")
    print(f"physical_realizations={physical_realizations}")
    print(f"slot_eligibility_unresolved={len(eligibility.unresolved)}")
    print()

    print("TIGHTENED RESULT")
    print(f"clean_same_build_rows={len(clean)}")
    print(f"same_build_resource_unresolved_count={len(unresolved_unique)}")
    print(f"states_pruned_below_incumbent={len(pruned)}")
    print(f"states_still_above_incumbent={len(survivors)}")
    print(f"ordinary_survivors={len(ordinary_survivors)}")
    print(f"twice_born_survivors={len(tbs_survivors)}")
    print()

    print("SURVIVORS AFTER SAME-BUILD RESOURCE TIGHTENING")
    for row in survivors:
        print(
            f"  {row.package} | flat_bound={row.flat_bound:.3f} "
            f"percent_bound={row.percent_bound:.6f} higher_resource={row.higher_resource:.3f} "
            f"resource_objective={row.resource_objective} provisioning={row.provisioning or '<none>'!r} "
            f"font_plus_defense_percent={row.mastery_percent:.6f} "
            f"optimistic_final={row.optimistic_final:.3f} twice_born={row.twice_born}"
        )
    print()

    print("PROOF STATUS")
    print(f"neutralized_armor_metadata_warning_count={len(neutralized_unique)}")
    print(f"same_build_resource_tightening_ready={bool(clean) and not eligibility.unresolved and not unresolved_unique}")
    print("final_weapon_damage_record_closed=False")
    print(
        "NEXT_STEP=resolve or exact-execute only the surviving named-set power mechanics. Rows pruned here cannot beat the 9451.238 incumbent even with their favorable semantic power ceilings because Font of Power now uses the actual same-build resource."
    )
    return 0 if clean and not eligibility.unresolved and not unresolved_unique else 2


if __name__ == "__main__":
    raise SystemExit(main())
