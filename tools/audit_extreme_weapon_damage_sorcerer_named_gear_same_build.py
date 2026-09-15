from __future__ import annotations

"""Canonical same-build Sorcerer check across resolved Weapon Damage gear states.

This audit closes the next coupling boundary in the Extreme Weapon Damage proof.
It takes every mechanic-complete physical named-gear Pareto state, materializes an
actual legal set witness, and evaluates that same witness for Max Magicka and Max
Stamina through the canonical named-gear character-sheet evaluator.

The Weapon Damage-preserving state is intentionally conservative on resource:
Altmer, pure Sorcerer, 64 attributes into the resource being tested, The Warrior,
best reviewed provisioning for that resource, active Emperor with six Home Keeps,
and either active bar. Resource jewelry, resource CP, and resource armor glyphs are
not added. Bloodthirsty/Physical-Harm jewelry, the reviewed Weapon Damage CP layer,
Dual Wield weapon package, Courage, and the Weapon Damage enchant remain represented
in the already-reviewed pre-class Weapon Damage subtotal because none are replaced
by this resource witness.

The resulting higher Max Resource is then fed directly into canonical Sorcerer
Class Mastery scoring for Font of Power + Calculated Defense and compared with the
strongest non-Sorcerer reviewed Class Mastery route at the identical pre-class
Weapon Damage baseline. No independent resource maximum is mixed in.
"""

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.character_build.character_class import CharacterClass
from minmax.character_progression import AttributeAllocation
from minmax.combat_state import EMPEROR_STATE_MARKER_PREFIX
from minmax.gear_set_repository import GearSetRepository
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
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate
from tools.audit_extreme_weapon_damage_joint_named_gear_realization import (
    _filtered_breakpoints,
    _filtered_eligibility,
    _filtered_topologies,
    _realized_pareto,
    _score_realization,
    _survivor_rows,
)
from tools.audit_extreme_weapon_damage_physical_gear_resource_requirements import (
    _best_non_sorcerer,
    _nongear_preclass_weapon_damage,
)
from tools.audit_extreme_weapon_damage_sorcerer_free_resource_witness import (
    _provisioning_candidates,
    _pure_sorcerer_route,
    _weapon_damage_mundus_name,
)
from tools.audit_extreme_weapon_damage_preweapon_upper_bound import _race_ceiling

DATABASE = ROOT / "data" / "eso.db"
WEAPON_OBJECTIVE = "weapon_damage"
RESOURCE_OBJECTIVES = ("max_magicka", "max_stamina")
EMPEROR_BUFF = f"{EMPEROR_STATE_MARKER_PREFIX}6"


@dataclass(frozen=True)
class _SameBuildRow:
    package: str
    preclass_weapon_damage: float
    incumbent_class: str
    incumbent_delta: float
    incumbent_mastery: tuple[str, ...]
    higher_resource: float
    resource_objective: str
    resource_active_bar: str
    provisioning: str
    sorcerer_delta: float
    sorcerer_percent: float
    sorcerer_mastery: tuple[str, ...]
    sorcerer_wins: bool
    projected_weapon_damage: float
    unresolved: tuple[str, ...]


def _physical_frontier_with_witnesses():
    repository = GearSetRepository(DATABASE)
    original_breakpoints, _pareto_rows, _unresolved_rows, survivor_by_key = _survivor_rows(repository)
    breakpoints = _filtered_breakpoints(original_breakpoints, survivor_by_key)
    eligibility = _filtered_eligibility(survivor_by_key)
    topologies = _filtered_topologies(repository, breakpoints)
    realization_service = ExtremeNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
    )

    scored = []
    witness_by_signature = {}
    for topology in topologies.topologies:
        result = realization_service.realize_topology(topology)
        for witness in result.realizations:
            score = _score_realization(witness, survivor_by_key)
            scored.append(score)
            witness_by_signature.setdefault(score.signature, witness)

    frontier = _realized_pareto(tuple(scored))
    pairs = []
    for score in frontier:
        witness = witness_by_signature.get(score.signature)
        if witness is None:
            raise RuntimeError(f"Physical Pareto state has no witness: {score.signature!r}")
        pairs.append((score, witness))
    return tuple(pairs), eligibility


def _resource_candidate(
    *,
    objective_key: str,
    active_bar: str,
    race_name: str,
    route,
):
    attributes = (
        AttributeAllocation(health=0, magicka=64, stamina=0)
        if objective_key == "max_magicka"
        else AttributeAllocation(health=0, magicka=0, stamina=64)
    )
    return ExtremeStructuralCandidate(
        race=race_name,
        class_route=route,
        attributes=attributes,
        active_bar=active_bar,
    )


def _best_resource_for_witness(
    *,
    witness,
    race_name: str,
    route,
    mundus_name: str,
    canonical: ExtremeCanonicalStructuralStatEvaluator,
):
    evaluator = ExtremeNamedGearCanonicalStatEvaluator(
        evaluator=canonical,
        realization=witness,
    )
    best = None
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
    return best, tuple(rows)


def main() -> int:
    nongear, components = _nongear_preclass_weapon_damage()
    frontier, eligibility = _physical_frontier_with_witnesses()
    race_name, _race_delta = _race_ceiling()
    mundus_name = _weapon_damage_mundus_name()
    route = _pure_sorcerer_route()
    mastery = ExtremeClassMasteryPairService(DATABASE)
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=ExtremeOptimizationService(database_path=DATABASE),
        progression_service=ExtremeHypotheticalClassProgressionService(DATABASE),
    )

    print("EXTREME WEAPON DAMAGE SORCERER NAMED-GEAR SAME-BUILD FRONTIER")
    print(f"database={DATABASE}")
    print(f"objective={WEAPON_OBJECTIVE}")
    print(f"weapon_damage_race={race_name!r}")
    print(f"weapon_damage_mundus={mundus_name!r}")
    print("pure_sorcerer=True")
    print(f"emperor_runtime_marker={EMPEROR_BUFF!r}")
    print("resource_named_gear_canonical_scoring=True")
    print("resource_jewelry_in_scope=False")
    print("resource_cp_in_scope=False")
    print("armor_resource_glyphs_in_scope=False")
    print("independent_resource_maximum_used=False")
    print()

    print("REVIEWED NON-GEAR PRE-CLASS WEAPON DAMAGE SUBTOTAL")
    for name, value in components:
        print(f"  {name}={value:.3f}")
    print(f"nongear_preclass_weapon_damage={nongear:.3f}")
    print()

    output_rows: list[_SameBuildRow] = []
    resource_unresolved: list[str] = []

    for gear, witness in frontier:
        reference = float(nongear) + float(gear.weapon_damage)
        incumbent = _best_non_sorcerer(mastery, reference)
        if incumbent is None or incumbent.projected_delta is None:
            resource_unresolved.append(
                f"{gear.signature!r}: no reviewed non-Sorcerer incumbent"
            )
            continue

        best_resource, resource_rows = _best_resource_for_witness(
            witness=witness,
            race_name=race_name,
            route=route,
            mundus_name=mundus_name,
            canonical=canonical,
        )
        if best_resource is None:
            resource_unresolved.append(
                f"{gear.signature!r}: no canonical named-gear resource score"
            )
            continue

        higher_resource, resource_objective, active_bar, provisioning, unresolved, _payload = best_resource
        sorcerer = mastery.best_for_class(
            CharacterClass.SORCERER,
            WEAPON_OBJECTIVE,
            reference_value=reference,
            higher_max_resource=float(higher_resource),
        )
        if sorcerer is None or sorcerer.projected_delta is None:
            resource_unresolved.append(
                f"{gear.signature!r}: Sorcerer Class Mastery score unavailable"
            )
            continue

        package = " + ".join(
            f"{name} {count}pc" for name, count in zip(gear.set_names, gear.counts)
        )
        incumbent_delta = float(incumbent.projected_delta)
        sorcerer_delta = float(sorcerer.projected_delta)
        sorcerer_wins = sorcerer_delta > incumbent_delta + 1e-9
        output_rows.append(
            _SameBuildRow(
                package=package,
                preclass_weapon_damage=reference,
                incumbent_class=incumbent.base_class.value,
                incumbent_delta=incumbent_delta,
                incumbent_mastery=tuple(incumbent.passive_names),
                higher_resource=float(higher_resource),
                resource_objective=str(resource_objective),
                resource_active_bar=str(active_bar),
                provisioning=str(provisioning),
                sorcerer_delta=sorcerer_delta,
                sorcerer_percent=float(sorcerer.percent),
                sorcerer_mastery=tuple(sorcerer.passive_names),
                sorcerer_wins=sorcerer_wins,
                projected_weapon_damage=reference + sorcerer_delta,
                unresolved=tuple(unresolved),
            )
        )
        resource_unresolved.extend(str(item) for item in unresolved if str(item))
        for row in resource_rows:
            resource_unresolved.extend(str(item) for item in row[4] if str(item))

    output_rows.sort(
        key=lambda row: (
            -row.projected_weapon_damage,
            -row.higher_resource,
            row.package.casefold(),
        )
    )

    print("SAME-BUILD RESOLVED GEAR STATES")
    print(f"physical_pareto_count={len(frontier)}")
    print(f"same_build_rows_scored={len(output_rows)}")
    winners = 0
    for row in output_rows:
        winners += int(row.sorcerer_wins and not row.unresolved)
        print(f"  {row.package}")
        print(f"    preclass_weapon_damage={row.preclass_weapon_damage:.3f}")
        print(
            f"    incumbent={row.incumbent_class} incumbent_delta={row.incumbent_delta:.3f} "
            f"mastery={row.incumbent_mastery!r}"
        )
        print(
            f"    canonical_higher_resource={row.higher_resource:.3f} "
            f"objective={row.resource_objective} active_bar={row.resource_active_bar} "
            f"provisioning={row.provisioning or '<none>'!r}"
        )
        print(
            f"    sorcerer_delta={row.sorcerer_delta:.3f} "
            f"sorcerer_percent={row.sorcerer_percent:.3f} "
            f"mastery={row.sorcerer_mastery!r}"
        )
        print(f"    sorcerer_beats_incumbent={row.sorcerer_wins}")
        print(f"    projected_weapon_damage={row.projected_weapon_damage:.3f}")
        print(f"    unresolved_count={len(row.unresolved)}")
        for message in row.unresolved[:3]:
            print(f"      unresolved: {message}")
        print()

    clean_unresolved = tuple(dict.fromkeys(message for message in resource_unresolved if message))
    clean_rows = tuple(row for row in output_rows if not row.unresolved)
    clean_winners = tuple(row for row in clean_rows if row.sorcerer_wins)
    best = clean_winners[0] if clean_winners else None

    print("FRONTIER SUMMARY")
    print(f"clean_same_build_rows={len(clean_rows)}")
    print(f"sorcerer_winning_resolved_states={len(clean_winners)}")
    if best is not None:
        print(f"best_resolved_sorcerer_package={best.package!r}")
        print(f"best_resolved_sorcerer_higher_resource={best.higher_resource:.3f}")
        print(f"best_resolved_sorcerer_projected_weapon_damage={best.projected_weapon_damage:.3f}")
        print(f"best_resolved_sorcerer_percent={best.sorcerer_percent:.3f}")
    print(f"slot_eligibility_unresolved={len(eligibility.unresolved)}")
    print(f"same_build_resource_unresolved_count={len(clean_unresolved)}")
    for message in clean_unresolved[:10]:
        print(f"  unresolved: {message}")
    if len(clean_unresolved) > 10:
        print(f"  ... {len(clean_unresolved) - 10} more")

    class_route_resolved_frontier_has_sorc_winner = bool(best is not None)
    print(f"resolved_frontier_has_sorcerer_winner={class_route_resolved_frontier_has_sorc_winner}")
    print("final_weapon_damage_class_route_closed=False")
    print("final_weapon_damage_record_closed=False")
    print(
        "NEXT_STEP=if a clean resolved Sorcerer winner exists, use it as the resolved-gear incumbent and "
        "resolve the retained unresolved named-set Weapon Damage mechanics against that incumbent; only after "
        "those proof blockers are bounded or mapped should the final whole-record snapshot be closed"
    )

    return 0 if frontier and clean_rows and not eligibility.unresolved else 2


if __name__ == "__main__":
    raise SystemExit(main())
