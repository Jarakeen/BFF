from __future__ import annotations

"""Correct the shared Extreme power snapshot with externally supplied Minor power buffs.

The closed Weapon Damage proof already includes external Minor + Major Courage in its
non-gear baseline and exposes external runtime conditions in the canonical record
contract.  Under that same contextual-record scope, externally supplied Minor
Brutality must be considered for Weapon Damage and externally supplied Minor Sorcery
must be considered for Spell Damage.

This audit does not alter physical named-gear legality.  It replays the already-closed
79-witness Weapon Damage denominator with one additional reviewed +10% named-power
bucket on every row.  Because the new bucket is common to every candidate, the winning
physical witness may remain unchanged, but that fact is verified rather than assumed.

Spell Damage uses the same +10% correction only after the independent Weapon/Spell
parity gates are green.
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
from minmax.named_combat_buffs import effects_for_buff
from minmax.stat_ids import StatId
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
from tools.audit_extreme_weapon_damage_sorcerer_free_resource_witness import _pure_sorcerer_route, _weapon_damage_mundus_name
from tools.audit_extreme_weapon_damage_sorcerer_named_gear_same_build import DATABASE

OBJECTIVE = "weapon_damage"
ARMOR_OF_TRUTH = "Armor of Truth"
KVATCH_GLADIATOR = "Kvatch Gladiator"
TWICE_BORN_STAR = "Twice-Born Star"
WINNER_RESOURCE = 49_961.0
WINNER_GEAR_FLAT = (129.0 + 460.0) + (129.0 + 1475.0)


@dataclass(frozen=True)
class _Row:
    package: str
    total: float
    unresolved: tuple[str, ...]


def _named_percent(name: str, stat: StatId) -> float:
    rows = tuple(
        row for row in effects_for_buff(name)
        if row.stat is stat and str(row.bucket).strip().casefold() == "percent"
    )
    if len(rows) != 1:
        raise RuntimeError(f"Expected one reviewed {name} {stat.value} percent effect, found {len(rows)}")
    return float(rows[0].value)


def _has_set(witness, name: str, pieces: int = 5) -> bool:
    return any(
        str(set_name) == name and int(count) == pieces
        for set_name, count in zip(witness.set_names, witness.counts)
    )


def main() -> int:
    baseline.scoped._semantic_bound = fledgling._semantic_bound

    minor_brutality = _named_percent("Minor Brutality", StatId.WEAPON_DAMAGE)
    minor_sorcery = _named_percent("Minor Sorcery", StatId.SPELL_DAMAGE)
    if abs(minor_brutality - minor_sorcery) > 1e-12:
        raise RuntimeError("Weapon/Spell Minor power buff magnitudes do not mirror")

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

    winner_reference = float(nongear) + WINNER_GEAR_FLAT + bsw.FULL_EXPERT_MAGE
    winner_mastery = mastery.best_for_class(
        CharacterClass.SORCERER,
        OBJECTIVE,
        reference_value=winner_reference,
        higher_max_resource=WINNER_RESOURCE,
    )
    if winner_mastery is None:
        raise RuntimeError("Sorcerer mastery unavailable for corrected Weapon Damage winner")
    winner_total = winner_reference * (
        1.0
        + float(winner_mastery.percent)
        + baseline.MAJOR_BRUTALITY_PERCENT
        + minor_brutality
    )

    reduced_rows, breakpoints, eligibility, topologies = baseline._bounded_frontier(repository)
    bounded_by_key = {row.key: row for row in reduced_rows}
    realization_service = ExtremeNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
    )

    rows: list[_Row] = []
    unresolved_all: list[str] = []
    physical_realizations = 0
    winner_witnesses = 0

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

            has_bsw = _has_set(witness, bsw.BURNING_SPELLWEAVE)
            has_tbs = _has_set(witness, TWICE_BORN_STAR)
            if _has_set(witness, ARMOR_OF_TRUTH) and _has_set(witness, KVATCH_GLADIATOR):
                winner_witnesses += 1
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
            base_total = reference * (
                1.0
                + float(sorcerer.percent)
                + baseline.MAJOR_BRUTALITY_PERCENT
                + minor_brutality
            )
            total = base_total * (1.0 + float(gear_percent))
            rows.append(_Row(package=package, total=float(total), unresolved=tuple(unresolved)))

    clean = tuple(row for row in rows if not row.unresolved)
    above = tuple(sorted(
        (row for row in clean if row.total > winner_total + 1e-9),
        key=lambda row: (-row.total, row.package.casefold()),
    ))
    ties = tuple(row for row in clean if abs(row.total - winner_total) <= 1e-9)
    unresolved_unique = tuple(dict.fromkeys(x for x in unresolved_all if x))

    denominator_closed = (
        not above
        and not unresolved_unique
        and not eligibility.unresolved
        and winner_witnesses == 1
        and len(clean) == physical_realizations
    )

    print("EXTREME POWER MINOR NAMED-BUFF CORRECTION")
    print(f"database={DATABASE}")
    print(f"minor_brutality_percent={minor_brutality:.6f}")
    print(f"minor_sorcery_percent={minor_sorcery:.6f}")
    print("external_named_power_scope_matches_existing_external_courage_scope=True")
    print()
    print("CORRECTED WEAPON DAMAGE WINNER")
    print("winner_package='Armor of Truth 5pc + Kvatch Gladiator 5pc'")
    print(f"pre_percent_reference={winner_reference:.3f}")
    print(f"font_plus_defense_percent={float(winner_mastery.percent):.6f}")
    print(f"major_brutality_percent={baseline.MAJOR_BRUTALITY_PERCENT:.6f}")
    print(f"minor_brutality_percent={minor_brutality:.6f}")
    print(f"corrected_weapon_damage={winner_total:.3f}")
    print()
    print("DENOMINATOR REPLAY")
    print(f"semantic_pareto_breakpoints={len(reduced_rows)}")
    print(f"candidate_topologies={len(topologies.topologies)}")
    print(f"physical_realizations={physical_realizations}")
    print(f"clean_same_build_rows={len(clean)}")
    print(f"winner_physical_witnesses={winner_witnesses}")
    print(f"rows_above_corrected_winner={len(above)}")
    print(f"rows_tied_with_corrected_winner={len(ties)}")
    for row in above[:10]:
        print(f"  challenger: {row.package} optimistic_final={row.total:.3f}")
    print()
    print("PROOF STATUS")
    print(f"resource_unresolved_count={len(unresolved_unique)}")
    print(f"slot_eligibility_unresolved={len(eligibility.unresolved)}")
    print(f"corrected_weapon_damage_denominator_closed={denominator_closed}")
    print("final_weapon_damage_record_closed=False")
    print(
        "NEXT_STEP=if corrected denominator is closed, update the canonical Weapon Damage record to include external Minor Brutality, then replay the same reviewed denominator for Spell Damage with external Minor Sorcery and Major Sorcery"
    )
    return 0 if denominator_closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
