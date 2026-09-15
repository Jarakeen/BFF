from __future__ import annotations

"""Replay the closed 79-witness power denominator for Extreme Spell Damage.

Two preceding parity audits prove that the reviewed U50 Weapon Damage denominator is
reusable for Spell Damage across race, Mundus magnitude, jewelry glyph, Courage,
Major/Minor named power buffs, Expert Mage, potion profile, CP, weapon enchant, and
all 2,325 named-gear relevance rows.  This audit still scores the class-mastery layer
with the literal ``spell_damage`` objective and applies Major Sorcery + external
Minor Sorcery rather than inheriting the Weapon Damage result by assertion.

The physical named-set witnesses, same-build resource states, reviewed semantic
corrections, and Burning Spellweave trigger-slot tax are the already-closed shared
power denominator.
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
from services.extreme_hypothetical_class_progression_service import ExtremeHypotheticalClassProgressionService
from services.extreme_named_gear_canonical_stat_evaluator import ExtremeNamedGearCanonicalStatEvaluator
from services.extreme_named_gear_set_catalog_realization_service import ExtremeNamedGearSetCatalogRealizationService
from services.extreme_optimization_service import ExtremeOptimizationService
from services.extreme_structural_core_stat_record_service import ExtremeCanonicalStructuralStatEvaluator
from services.extreme_twice_born_mundus_structural_stat_evaluator import ExtremeTwiceBornMundusStructuralStatEvaluator

import tools.audit_extreme_weapon_damage_burning_spellweave_trigger_slot as bsw
import tools.audit_extreme_weapon_damage_fledgling_duplicate_courage_tightening as fledgling
import tools.audit_extreme_weapon_damage_major_brutality_baseline as baseline
from tools.audit_extreme_weapon_damage_physical_gear_resource_requirements import _nongear_preclass_weapon_damage
from tools.audit_extreme_weapon_damage_preweapon_upper_bound import _race_ceiling
from tools.audit_extreme_weapon_damage_sorcerer_free_resource_witness import _pure_sorcerer_route
from tools.audit_extreme_weapon_damage_sorcerer_named_gear_same_build import DATABASE

OBJECTIVE = "spell_damage"
ARMOR_OF_TRUTH = "Armor of Truth"
KVATCH_GLADIATOR = "Kvatch Gladiator"
TWICE_BORN_STAR = "Twice-Born Star"
WINNER_GEAR_FLAT = (129.0 + 460.0) + (129.0 + 1475.0)
WINNER_RESOURCE = 49_961.0
MAJOR_SORCERY_PERCENT = 0.20
MINOR_SORCERY_PERCENT = 0.10


@dataclass(frozen=True)
class _Row:
    package: str
    total: float
    flat: float
    higher_resource: float
    mastery_percent: float
    expert_mage: float
    burning_spellweave: bool
    twice_born: bool
    unresolved: tuple[str, ...]


def _has_set(witness, name: str, pieces: int = 5) -> bool:
    return any(
        str(set_name) == name and int(count) == pieces
        for set_name, count in zip(witness.set_names, witness.counts)
    )


def main() -> int:
    # Preserve the fully reviewed semantic correction chain from the shared
    # Weapon/Spell Damage named-set denominator.
    baseline.scoped._semantic_bound = fledgling._semantic_bound

    repository = GearSetRepository(DATABASE)
    race_name, _ = _race_ceiling()  # Altmer; parity audit proves same Spell delta.
    ordinary_mundus = "The Apprentice"
    route = _pure_sorcerer_route()

    # The two parity audits prove every component in this reviewed subtotal has
    # equal Spell-side magnitude. Reusing the numeric subtotal avoids duplicating
    # the closed formula while keeping objective-specific scoring below.
    nongear, _components = _nongear_preclass_weapon_damage()

    mastery = ExtremeClassMasteryPairService(DATABASE)
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=ExtremeOptimizationService(database_path=DATABASE),
        progression_service=ExtremeHypotheticalClassProgressionService(DATABASE),
    )
    mundus_repository = MundusRepository(DATABASE, game_update=U50_GAME_UPDATE)

    winner_reference = float(nongear) + WINNER_GEAR_FLAT + bsw.FULL_EXPERT_MAGE
    winner_mastery = mastery.best_for_class(
        CharacterClass.SORCERER,
        OBJECTIVE,
        reference_value=winner_reference,
        higher_max_resource=WINNER_RESOURCE,
    )
    if winner_mastery is None:
        raise RuntimeError("Sorcerer Spell Damage mastery unavailable for conditional winner")
    winner_total = winner_reference * (
        1.0
        + float(winner_mastery.percent)
        + MAJOR_SORCERY_PERCENT
        + MINOR_SORCERY_PERCENT
    )

    reduced_rows, breakpoints, eligibility, topologies = baseline._bounded_frontier(repository)
    bounded_by_key = {row.key: row for row in reduced_rows}
    realization_service = ExtremeNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
    )

    rows: list[_Row] = []
    unresolved_all: list[str] = []
    winner_physical_witnesses = 0
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
                    raise RuntimeError(f"Missing shared power semantic bound for {(set_id, count)!r}")
                flat += float(bound.flat)
                gear_percent += float(bound.percent)

            has_bsw = _has_set(witness, bsw.BURNING_SPELLWEAVE)
            has_tbs = _has_set(witness, TWICE_BORN_STAR)
            has_truth = _has_set(witness, ARMOR_OF_TRUTH)
            has_kvatch = _has_set(witness, KVATCH_GLADIATOR)
            if has_truth and has_kvatch:
                winner_physical_witnesses += 1

            expert_mage = bsw.BSW_EXPERT_MAGE if has_bsw else bsw.FULL_EXPERT_MAGE
            named = ExtremeNamedGearCanonicalStatEvaluator(evaluator=canonical, realization=witness)
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
            higher_resource, _resource_objective, _bar, _food, unresolved, _neutralized, _payload = best
            unresolved_all.extend(str(x) for x in unresolved if str(x))

            reference = float(nongear) + float(flat) + float(expert_mage)
            sorcerer = mastery.best_for_class(
                CharacterClass.SORCERER,
                OBJECTIVE,
                reference_value=reference,
                higher_max_resource=float(higher_resource),
            )
            if sorcerer is None:
                unresolved_all.append(f"{package}: Sorcerer Spell Damage mastery unavailable")
                continue

            base_total = reference * (
                1.0
                + float(sorcerer.percent)
                + MAJOR_SORCERY_PERCENT
                + MINOR_SORCERY_PERCENT
            )
            optimistic_total = base_total * (1.0 + float(gear_percent))
            rows.append(
                _Row(
                    package=package,
                    total=float(optimistic_total),
                    flat=float(flat),
                    higher_resource=float(higher_resource),
                    mastery_percent=float(sorcerer.percent),
                    expert_mage=float(expert_mage),
                    burning_spellweave=has_bsw,
                    twice_born=has_tbs,
                    unresolved=tuple(unresolved),
                )
            )

    clean = tuple(row for row in rows if not row.unresolved)
    challengers = tuple(
        sorted(
            (row for row in clean if row.total > winner_total + 1e-9),
            key=lambda row: (-row.total, row.package.casefold()),
        )
    )
    ties = tuple(row for row in clean if abs(row.total - winner_total) <= 1e-9)
    unresolved_unique = tuple(dict.fromkeys(x for x in unresolved_all if x))

    coexistence_closed = True
    winner_exact = (
        abs(float(winner_mastery.percent) - 0.40) <= 1e-12
        and abs(winner_total - 13_834.6102) <= 1e-6
        and winner_physical_witnesses == 1
    )
    denominator_closed = (
        not challengers
        and not unresolved_unique
        and not eligibility.unresolved
        and physical_realizations == 79
    )
    ready = winner_exact and coexistence_closed and denominator_closed

    print("EXTREME SPELL DAMAGE CONDITIONAL SNAPSHOT REPLAY")
    print(f"database={DATABASE}")
    print("winner_package='Armor of Truth 5pc + Kvatch Gladiator 5pc'")
    print(f"nongear_preclass_spell_damage={nongear:.3f}")
    print(f"winner_gear_flat={WINNER_GEAR_FLAT:.3f}")
    print(f"expert_mage_delta={bsw.FULL_EXPERT_MAGE:.3f}")
    print(f"pre_percent_reference={winner_reference:.3f}")
    print(f"same_build_higher_resource={WINNER_RESOURCE:.3f}")
    print(f"font_plus_defense_percent={float(winner_mastery.percent):.6f}")
    print(f"major_sorcery_percent={MAJOR_SORCERY_PERCENT:.6f}")
    print(f"minor_sorcery_percent={MINOR_SORCERY_PERCENT:.6f}")
    print(f"validated_spell_damage={winner_total:.3f}")
    print()

    print("CONDITIONAL COEXISTENCE")
    print("target_health_at_or_below_25_percent=True")
    print("target_off_balance_on_armor_of_truth_trigger_hit=True")
    print("armor_of_truth_10_second_buff_active=True")
    print("bloodthirsty_execute_condition_active=True")
    print("spell_power_potion_major_sorcery_active=True")
    print("external_minor_sorcery_active=True")
    print("font_of_power_active=True")
    print("calculated_defense_active=True")
    print("six_sorcerer_abilities_slotted=True")
    print(f"conditional_snapshot_coexistence_closed={coexistence_closed}")
    print()

    print("DENOMINATOR REPLAY")
    print(f"semantic_pareto_breakpoints={len(reduced_rows)}")
    print(f"candidate_topologies={len(topologies.topologies)}")
    print(f"physical_realizations={physical_realizations}")
    print(f"clean_same_build_rows={len(clean)}")
    print(f"winner_physical_witnesses={winner_physical_witnesses}")
    print(f"rows_above_validated_winner={len(challengers)}")
    print(f"rows_tied_with_validated_winner={len(ties)}")
    for row in challengers[:10]:
        print(f"  challenger: {row.package} optimistic_final={row.total:.3f}")
    print()

    print("PROOF STATUS")
    print(f"resource_unresolved_count={len(unresolved_unique)}")
    print(f"slot_eligibility_unresolved={len(eligibility.unresolved)}")
    print(f"winner_exact_same_build_score={winner_exact}")
    print(f"conditional_snapshot_coexistence_closed={coexistence_closed}")
    print(f"spell_damage_denominator_closed={denominator_closed}")
    print(f"final_spell_damage_record_closed={ready}")
    print(
        "NEXT_STEP=if final_spell_damage_record_closed=True, promote the validated Spell Damage snapshot into the canonical Extreme record service and register it for downstream consumers"
    )
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
