from __future__ import annotations

"""Tighten Burning Spellweave survivors with the legal Flame-trigger slot cost.

The potion-active Weapon Damage frontier previously credits Burning Spellweave's
reviewed +490 Weapon/Spell Damage proc while also granting the maximum pure-Sorcerer
Expert Mage value from six Sorcerer abilities on the active bar.

Burning Spellweave requires damage from a Flame Damage ability.  The repository has
a canonical `scalding_rune` component and current reviewed game data identifies
Scalding Rune as a Mages Guild Flame Damage active ability.  It is therefore a legal
self-trigger for the proc while retaining the proven Dual-Wield weapon topology, but
it is not a Sorcerer ability.  A BSW-active snapshot must consequently reserve one of
six active-bar slots for Scalding Rune, reducing Expert Mage from 6 * 108 to 5 * 108.

This audit reuses every semantic correction in the Fledgling/Oakensoul/potion-active
frontier and changes only the Expert Mage contribution for physical witnesses that
contain Burning Spellweave 5pc.  The resolved incumbent remains unchanged because it
does not use Burning Spellweave.  Other conditional set triggers remain favorable
until their own coexistence boundary is reviewed.
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

import tools.audit_extreme_weapon_damage_fledgling_duplicate_courage_tightening as fledgling
import tools.audit_extreme_weapon_damage_major_brutality_baseline as baseline
from tools.audit_extreme_weapon_damage_physical_gear_resource_requirements import (
    _nongear_preclass_weapon_damage,
)
from tools.audit_extreme_weapon_damage_preweapon_upper_bound import _race_ceiling
from tools.audit_extreme_weapon_damage_sorcerer_free_resource_witness import (
    _pure_sorcerer_route,
    _weapon_damage_mundus_name,
)
from tools.audit_extreme_weapon_damage_sorcerer_named_gear_same_build import DATABASE

OBJECTIVE = "weapon_damage"
BURNING_SPELLWEAVE = "Burning Spellweave"
TWICE_BORN_STAR = "Twice-Born Star"
EXPERT_MAGE_PER_SORCERER_SLOT = 108.0
FULL_EXPERT_MAGE = 6.0 * EXPERT_MAGE_PER_SORCERER_SLOT
BSW_EXPERT_MAGE = 5.0 * EXPERT_MAGE_PER_SORCERER_SLOT
SCALDING_RUNE = "scalding_rune"


@dataclass(frozen=True)
class _Row:
    package: str
    flat_bound: float
    higher_resource: float
    mastery_percent: float
    expert_mage: float
    total: float
    burning_spellweave: bool
    twice_born: bool
    unresolved: tuple[str, ...]


def _has_set(witness, name: str, pieces: int) -> bool:
    return any(
        str(set_name) == name and int(count) == pieces
        for set_name, count in zip(witness.set_names, witness.counts)
    )


def main() -> int:
    # Preserve the full inherited semantic correction chain.
    baseline.scoped._semantic_bound = fledgling._semantic_bound

    repository = GearSetRepository(DATABASE)
    race_name, _ = _race_ceiling()
    ordinary_mundus = _weapon_damage_mundus_name()
    route = _pure_sorcerer_route()
    nongear, _components = _nongear_preclass_weapon_damage()
    mastery = ExtremeClassMasteryPairService(DATABASE)
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=ExtremeOptimizationService(database_path=DATABASE),
        progression_service=ExtremeHypotheticalClassProgressionService(DATABASE),
    )
    mundus_repository = MundusRepository(DATABASE, game_update=U50_GAME_UPDATE)

    incumbent, resolved_eligibility, resolved_unresolved = baseline._resolved_incumbent(
        canonical=canonical,
        mastery=mastery,
        race_name=race_name,
        route=route,
        mundus_name=ordinary_mundus,
        nongear=nongear,
        expert_mage=FULL_EXPERT_MAGE,
    )
    incumbent_total = float(incumbent[0])

    reduced_rows, breakpoints, eligibility, topologies = baseline._bounded_frontier(repository)
    bounded_by_key = {row.key: row for row in reduced_rows}
    realization_service = ExtremeNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
    )

    rows: list[_Row] = []
    unresolved_all: list[str] = []
    physical_realizations = 0
    for topology in topologies.topologies:
        result = realization_service.realize_topology(topology)
        for witness in result.realizations:
            physical_realizations += 1
            flat = 0.0
            gear_percent = 0.0
            for set_id, count in zip(witness.set_ids, witness.counts):
                bound = bounded_by_key.get((int(set_id), int(count)))
                if bound is None:
                    raise RuntimeError(f"Missing semantic bound for {(set_id, count)!r}")
                flat += float(bound.flat)
                gear_percent += float(bound.percent)

            has_bsw = _has_set(witness, BURNING_SPELLWEAVE, 5)
            has_tbs = _has_set(witness, TWICE_BORN_STAR, 5)
            expert_mage = BSW_EXPERT_MAGE if has_bsw else FULL_EXPERT_MAGE

            named = ExtremeNamedGearCanonicalStatEvaluator(
                evaluator=canonical,
                realization=witness,
            )
            if has_tbs:
                evaluator = ExtremeTwiceBornMundusStructuralStatEvaluator(
                    evaluator=named,
                    mundus_repository=mundus_repository,
                )
                resource_rows = baseline._resource_rows_for_evaluator(
                    evaluator,
                    race_name=race_name,
                    route=route,
                    ordinary_mundus=None,
                )
            else:
                resource_rows = baseline._resource_rows_for_evaluator(
                    named,
                    race_name=race_name,
                    route=route,
                    ordinary_mundus=ordinary_mundus,
                )
            best = baseline._best_resource(resource_rows)
            package = " + ".join(
                f"{name} {count}pc" for name, count in zip(witness.set_names, witness.counts)
            )
            if best is None:
                unresolved_all.append(f"{package}: no resource score")
                continue
            higher_resource, _objective, _bar, _food, unresolved, _neutralized, _payload = best
            unresolved_all.extend(str(x) for x in unresolved if str(x))

            reference = float(nongear) + float(flat) + float(expert_mage)
            sorcerer = mastery.best_for_class(
                CharacterClass.SORCERER,
                OBJECTIVE,
                reference_value=reference,
                higher_max_resource=float(higher_resource),
            )
            if sorcerer is None:
                unresolved_all.append(f"{package}: Sorcerer mastery unavailable")
                continue
            baseline_total = reference * (
                1.0 + float(sorcerer.percent) + baseline.MAJOR_BRUTALITY_PERCENT
            )
            optimistic = baseline_total * (1.0 + float(gear_percent))
            rows.append(
                _Row(
                    package=package,
                    flat_bound=float(flat),
                    higher_resource=float(higher_resource),
                    mastery_percent=float(sorcerer.percent),
                    expert_mage=float(expert_mage),
                    total=float(optimistic),
                    burning_spellweave=has_bsw,
                    twice_born=has_tbs,
                    unresolved=tuple(unresolved),
                )
            )

    clean = tuple(row for row in rows if not row.unresolved)
    pruned = tuple(row for row in clean if row.total <= incumbent_total + 1e-9)
    survivors = tuple(
        sorted(
            (row for row in clean if row.total > incumbent_total + 1e-9),
            key=lambda row: (-row.total, row.package.casefold()),
        )
    )
    bsw_survivors = tuple(row for row in survivors if row.burning_spellweave)
    unresolved_unique = tuple(dict.fromkeys(x for x in unresolved_all if x))

    print("EXTREME WEAPON DAMAGE BURNING SPELLWEAVE TRIGGER-SLOT TIGHTENING")
    print(f"database={DATABASE}")
    print(f"resolved_potion_active_incumbent={incumbent_total:.3f}")
    print(f"burning_spellweave_trigger_skill={SCALDING_RUNE!r}")
    print("burning_spellweave_trigger_skill_line='Mages Guild'")
    print("burning_spellweave_trigger_damage_type='Flame Damage'")
    print(f"expert_mage_per_sorcerer_slot={EXPERT_MAGE_PER_SORCERER_SLOT:.3f}")
    print(f"ordinary_expert_mage_delta={FULL_EXPERT_MAGE:.3f}")
    print(f"burning_spellweave_expert_mage_delta={BSW_EXPERT_MAGE:.3f}")
    print("dual_wield_topology_preserved=True")
    print("burning_spellweave_proc_still_favorably_assumed_active=True")
    print()

    print("RESULT")
    print(f"semantic_pareto_breakpoints={len(reduced_rows)}")
    print(f"candidate_topologies={len(topologies.topologies)}")
    print(f"physical_realizations={physical_realizations}")
    print(f"clean_same_build_rows={len(clean)}")
    print(f"states_pruned_below_incumbent={len(pruned)}")
    print(f"states_still_above_incumbent={len(survivors)}")
    print(f"burning_spellweave_survivors={len(bsw_survivors)}")
    print(f"ordinary_survivors={sum(1 for row in survivors if not row.twice_born)}")
    print(f"twice_born_survivors={sum(1 for row in survivors if row.twice_born)}")
    print()

    print("SURVIVORS")
    for row in survivors:
        print(
            f"  {row.package} | flat_bound={row.flat_bound:.3f} "
            f"higher_resource={row.higher_resource:.3f} "
            f"expert_mage={row.expert_mage:.3f} "
            f"font_plus_defense_percent={row.mastery_percent:.6f} "
            f"optimistic_final={row.total:.3f} "
            f"burning_spellweave={row.burning_spellweave} twice_born={row.twice_born}"
        )

    print()
    print("PROOF STATUS")
    print(f"resource_unresolved_count={len(unresolved_unique)}")
    print(f"resolved_frontier_unresolved_count={len(resolved_unresolved)}")
    print(f"slot_eligibility_unresolved={len(eligibility.unresolved) + len(resolved_eligibility.unresolved)}")
    ready = not unresolved_unique and not resolved_unresolved and not eligibility.unresolved and not resolved_eligibility.unresolved
    print(f"burning_spellweave_trigger_slot_tightening_ready={ready}")
    print("final_weapon_damage_record_closed=False")
    print(
        "NEXT_STEP=review simultaneous runtime legality for the remaining conditional-power survivors; "
        "Burning Spellweave rows already pay one active-bar slot for canonical Scalding Rune and therefore "
        "cannot claim the six-Sorcerer-slot Expert Mage maximum at the same snapshot"
    )
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
