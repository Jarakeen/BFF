from __future__ import annotations

"""Strict final closure for the Extreme Health Recovery theoretical maximum.

This companion audit keeps the broad final-record composition small while closing the
last cross-axis details: potion-backed Major Fortitude, non-slottable Champion Point
Recovery, same-build Enlivening Overflow, and the Destruction-Staff gear witness used
by the proven Force Shock / Baron / Decisive stochastic refill route.
"""

import argparse
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.base_character_state import BASE_HEALTH_RECOVERY, BASE_MAX_MAGICKA, MAGICKA_PER_ATTRIBUTE
from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.combat_effect_semantics import GameUpdate
from minmax.gear_set_repository import GearSetRepository
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.named_combat_buffs import effects_for_buff
from minmax.passive_math import heavy_armor_constitution_health_recovery_percent
from minmax.potion_availability_repository import PotionAvailabilityRepository
from minmax.race_repository import RaceRepository
from minmax.stat_ids import StatId
from minmax.ultimate_resource_timeline import UltimateGenerationEvent
from services.extreme_armor_weight_filtered_slot_eligibility_service import (
    ExtremeArmorWeightFilteredSlotEligibilityService,
)
from services.extreme_champion_point_objective_service import ExtremeChampionPointObjectiveService
from services.extreme_externalized_named_gear_constraint_search_service import (
    ExtremeExternalizedNamedGearConstraintSearchService,
    ExtremeExternalizedNamedGearSemantic,
)
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_health_recovery_champion_point_branch_service import (
    ExtremeHealthRecoveryChampionPointBranchService,
)
from services.extreme_health_recovery_champion_point_screening_service import (
    ExtremeHealthRecoveryChampionPointScreeningService,
)
from services.extreme_health_recovery_jewelry_projection_service import (
    ExtremeHealthRecoveryJewelryProjectionService,
)
from services.extreme_health_recovery_passive_special_branch_service import (
    ExtremeHealthRecoveryPassiveSpecialBranchService,
)
from services.extreme_health_recovery_runtime_compatibility_service import (
    ExtremeHealthRecoveryCompatibility,
    ExtremeHealthRecoveryRuntimeCompatibilityService,
    ExtremeHealthRecoveryRuntimeState,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_passive_projection_service import ExtremePassiveProjectionService
from services.extreme_recovery_final_score_service import (
    ExtremeRecoveryFinalScoreService,
    ExtremeRecoveryProofGate,
    ExtremeRecoveryScoreComponent,
)
from services.extreme_recovery_potion_projection_service import ExtremeRecoveryPotionProjectionService
from services.extreme_recovery_provisioning_projection_service import (
    ExtremeRecoveryProvisioningProjectionService,
)
from services.extreme_skill_universe_service import ExtremeSkillDomain, ExtremeSkillUniverseService
from services.extreme_constrained_named_gear_exact_flat_search_service import ExtremeNamedGearRequirement
from tools.audit_extreme_health_recovery_final_record import (
    _armor_magicka_glyph_flat,
    _armor_witness,
    _class_witness,
    _destro_compatible,
    _provisioning_magicka,
    _race_witness,
    _set_magicka_effects,
    _special_catalog,
)


OBJECTIVE = "health_recovery"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _non_slottable_cp(database: Path):
    repository = ChampionPointStaticRepository(database)
    baseline = ExtremeChampionPointObjectiveService.non_slottable_baseline_for_objective(
        repository, OBJECTIVE
    )
    total = float(baseline.reviewed_lower_bound)
    unresolved = []
    included = [
        (row.name, float(row.reviewed_delta or 0.0), "static")
        for row in baseline.resolved_candidates
        if float(row.reviewed_delta or 0.0) != 0.0
    ]
    for candidate in baseline.unresolved_candidates:
        record = repository.get(candidate.name)
        if record is None:
            unresolved.append(f"non-slottable CP record missing: {candidate.name}")
            continue
        screening = ExtremeHealthRecoveryChampionPointScreeningService.screen(record)
        if not screening.relevant:
            continue
        branch = ExtremeHealthRecoveryChampionPointBranchService.classify(record)
        if not branch.complete or branch.flat_ceiling is None:
            unresolved.extend(
                branch.unresolved or (f"non-slottable CP branch unresolved: {candidate.name}",)
            )
            continue
        total += float(branch.flat_ceiling)
        included.append((candidate.name, float(branch.flat_ceiling), branch.condition or "dynamic"))
    return total, tuple(included), tuple(dict.fromkeys(unresolved))


def _slottable_cp(database: Path, *, max_magicka: float):
    from tools.audit_extreme_health_recovery_final_record import _cp_candidates

    return _cp_candidates(database, max_magicka=max_magicka)


def _shared_passives(database: Path):
    flat = 0.0
    percent = 0.0
    sources = []
    domination = None
    for passive in ExtremeSkillUniverseService(database).all_player_skills():
        if not passive.is_passive:
            continue
        if passive.name.casefold() == "domination":
            branch = ExtremeHealthRecoveryPassiveSpecialBranchService.classify(passive)
            if branch is not None and branch.percent_ceiling is not None:
                domination = branch
            continue
        if passive.domain in {ExtremeSkillDomain.RACIAL, ExtremeSkillDomain.CLASS}:
            continue
        projection = ExtremePassiveProjectionService.project(passive)
        for row in projection.contributions:
            if row.objective_key != OBJECTIVE:
                continue
            flat += float(row.flat)
            percent += float(row.percent_of_reference) * 100.0
            sources.append(row.source)
    return flat, percent, tuple(sources), domination


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    unresolved: list[str] = []
    gates: list[ExtremeRecoveryProofGate] = []

    race, racial_unresolved, racial_rows = _race_witness(database)
    race_name = race[2].skill_line.removesuffix(" Skills") if race else ""
    race_flat = float(race[0]) if race else 0.0
    gates.append(ExtremeRecoveryProofGate("race_dominance", bool(race and len(racial_rows) == 1 and not racial_unresolved)))
    unresolved.extend(f"racial recovery mention unresolved: {name}" for name in racial_unresolved)

    class_row, class_unresolved = _class_witness(database)
    class_flat = float(class_row.class_flat_ceiling or 0.0) if class_row else 0.0
    gates.append(ExtremeRecoveryProofGate("class_route_dominance", bool(class_row and not class_unresolved)))
    unresolved.extend(item for row in class_unresolved for item in row.unresolved)

    armor = _armor_witness(database)
    armor_flat = float(armor[0]) if armor else 0.0
    gates.append(ExtremeRecoveryProofGate("seven_heavy_armor_mundus_frontier", armor is not None))

    jewelry = ExtremeHealthRecoveryJewelryProjectionService(
        JewelryGlyphEffectRepository(database), JewelryTraitRepository(database)
    ).build()
    jewelry_flat = float(jewelry.three_slot_infused_flat or 0.0)
    gates.append(ExtremeRecoveryProofGate("jewelry_frontier", jewelry.denominator_proven and jewelry.three_slot_infused_flat is not None))
    unresolved.extend(jewelry.unresolved)

    provisioning = ExtremeRecoveryProvisioningProjectionService.build(database, objective_key=OBJECTIVE)
    drink = provisioning.drink
    drink_flat = float(drink.delta) if drink else 0.0
    gates.append(ExtremeRecoveryProofGate("drink_provisioning_frontier", provisioning.comparison_proven and drink is not None))
    unresolved.extend(provisioning.unresolved)

    potion = ExtremeRecoveryPotionProjectionService(
        PotionAvailabilityRepository(database, game_update=GameUpdate.U50)
    ).build(OBJECTIVE)
    major_fortitude_available = potion.denominator_proven and "Major Fortitude" in potion.relevant_buffs
    gates.append(ExtremeRecoveryProofGate("major_fortitude_potion_source", major_fortitude_available))
    unresolved.extend(potion.unresolved)

    gear_repository = GearSetRepository(database)
    topology = ExtremeGearSetTopologyCatalogService(gear_repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(gear_repository).build()
    raw_eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    filtered = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        database, raw_eligibility, required_armor_weight="Heavy"
    )
    relevance = ExtremeGearSetObjectiveRelevanceService(gear_repository).build(OBJECTIVE, breakpoints)
    special, special_unresolved = _special_catalog(relevance)
    adamant = next((row for row in special.positive_challengers if row.set_name == "Adamant Lurker"), None)
    gear_search = ExtremeExternalizedNamedGearConstraintSearchService.search(
        topology_catalog=topology,
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=relevance,
        requirements=(
            ExtremeNamedGearRequirement("Adamant Lurker", 5),
            ExtremeNamedGearRequirement("Baron Zaudrus", 2),
        ),
        externalized=(ExtremeExternalizedNamedGearSemantic("Adamant Lurker", 5),),
    )
    eligibility_by_id = {int(row.set_id): row for row in filtered.catalog.sets}
    realizations = () if gear_search.search is None else gear_search.search.realizations
    destro_realizations = tuple(row for row in realizations if _destro_compatible(row, eligibility_by_id))
    ordinary_gear_flat = float(gear_search.search.best_exact_flat_delta or 0.0) if gear_search.search else 0.0
    adamant_flat = float(adamant.flat_ceiling or 0.0) if adamant else 0.0
    adamant_runtime = bool(
        adamant
        and ExtremeHealthRecoveryRuntimeCompatibilityService.assess(
            adamant, ExtremeHealthRecoveryRuntimeState()
        ).status is ExtremeHealthRecoveryCompatibility.COMPATIBLE
    )
    gates.extend((
        ExtremeRecoveryProofGate("heavy_named_gear_search", filtered.denominator_proven and gear_search.winner_found),
        ExtremeRecoveryProofGate("adamant_runtime", adamant_runtime),
        ExtremeRecoveryProofGate("destruction_staff_realization", bool(destro_realizations)),
        ExtremeRecoveryProofGate("special_named_gear_frontier_checkpoint", True, "Closed by the constrained-special, Willow, and Oakensoul audits."),
        ExtremeRecoveryProofGate("stochastic_ultimate_refill_checkpoint", True, "Closed by the Force Shock / Baron + Decisive all-procs witness."),
    ))
    unresolved.extend(special_unresolved)
    unresolved.extend(gear_search.unresolved)

    race_map = RaceRepository(database).get_stat_map_by_name(race_name) if race_name else {}
    race_magicka = float(race_map.get("max_magicka", 0.0))
    armor_magicka = _armor_magicka_glyph_flat(database)
    if armor_magicka is None:
        unresolved.append("canonical Max Magicka armor glyph value unresolved")
        armor_magicka = 0.0
    provisioning_magicka_flat = provisioning_magicka_percent = 0.0
    if drink is not None:
        provisioning_magicka_flat, provisioning_magicka_percent, provisioning_unresolved = _provisioning_magicka(database, drink.name)
        # Provisioning parser diagnostics are relevant here only when the selected
        # drink actually carries a Max Magicka effect that this proof consumes.
        if provisioning_magicka_flat or provisioning_magicka_percent:
            unresolved.extend(provisioning_unresolved)

    from minmax.passive_math import mages_guild_magicka_controller_percent, undaunted_mettle_resource_percent

    free_magicka_percent = undaunted_mettle_resource_percent(1) + mages_guild_magicka_controller_percent(3)
    best_realization = None
    best_max_magicka = -1.0
    best_set_magicka_sources = ()
    for realization in destro_realizations:
        set_flat, set_percent, set_sources = _set_magicka_effects(gear_repository, realization)
        pre_percent = (
            float(BASE_MAX_MAGICKA)
            + 64.0 * float(MAGICKA_PER_ATTRIBUTE)
            + race_magicka
            + float(armor_magicka)
            + provisioning_magicka_flat
            + set_flat
        )
        value = pre_percent * (
            1.0 + free_magicka_percent + provisioning_magicka_percent + set_percent
        )
        if value > best_max_magicka + 1e-9:
            best_max_magicka = value
            best_realization = realization
            best_set_magicka_sources = set_sources
    if best_realization is None:
        best_max_magicka = 0.0
    gates.append(ExtremeRecoveryProofGate("same_build_max_magicka_witness", best_realization is not None))

    non_slottable_cp, non_slottable_rows, non_slottable_unresolved = _non_slottable_cp(database)
    unresolved.extend(non_slottable_unresolved)
    cp_loadout, cp_unresolved = _slottable_cp(database, max_magicka=best_max_magicka)
    unresolved.extend(cp_unresolved)
    state = ExtremeHealthRecoveryRuntimeState(
        max_magicka=best_max_magicka,
        ultimate_generation_events=(
            UltimateGenerationEvent(24.0, 250.0, "proven complete post-cast Ultimate refill"),
        ),
    )
    cp_runtime = ExtremeHealthRecoveryRuntimeCompatibilityService.assess_champion_points(
        cp_loadout.selected, state
    )
    cp_runtime_ok = all(row.status is ExtremeHealthRecoveryCompatibility.COMPATIBLE for row in cp_runtime)
    gates.extend((
        ExtremeRecoveryProofGate("non_slottable_cp_denominator", not non_slottable_unresolved),
        ExtremeRecoveryProofGate("cp_loadout_legality", cp_loadout.denominator_proven),
        ExtremeRecoveryProofGate("cp_runtime_compatibility", cp_runtime_ok),
        ExtremeRecoveryProofGate("cp_frontier_checkpoint", True, "Health Recovery CP semantic/loadout denominator was closed by the equipment-frontier audit."),
    ))
    for row in cp_runtime:
        if row.status is not ExtremeHealthRecoveryCompatibility.COMPATIBLE:
            unresolved.append(f"{row.candidate.name}: {row.reason}")

    fortitude = tuple(row for row in effects_for_buff("Major Fortitude") if row.stat is StatId.HEALTH_RECOVERY)
    fortitude_percent = float(fortitude[0].value) * 100.0 if len(fortitude) == 1 else 0.0
    gates.append(ExtremeRecoveryProofGate("major_fortitude_semantics", len(fortitude) == 1))
    constitution_percent = heavy_armor_constitution_health_recovery_percent(7) * 100.0

    shared_flat, shared_percent, shared_sources, domination = _shared_passives(database)
    domination_percent = float(domination.percent_ceiling or 0.0) if domination else 0.0
    gates.append(ExtremeRecoveryProofGate(
        "emperor_domination_six_home_keeps",
        bool(domination and domination.can_raise_self and domination_percent > 0.0),
    ))

    additive = (
        ExtremeRecoveryScoreComponent(f"racial:{race_name or '<unresolved>'}", race_flat),
        ExtremeRecoveryScoreComponent("class_route", class_flat),
        ExtremeRecoveryScoreComponent("armor_mundus_traits", armor_flat),
        ExtremeRecoveryScoreComponent("three_infused_jewelry_recovery_glyphs", jewelry_flat),
        ExtremeRecoveryScoreComponent(f"drink:{drink.name if drink else '<unresolved>'}", drink_flat),
        ExtremeRecoveryScoreComponent("ordinary_named_gear", ordinary_gear_flat),
        ExtremeRecoveryScoreComponent("Adamant Lurker 5pc", adamant_flat),
        ExtremeRecoveryScoreComponent("non_slottable_Champion_Points", non_slottable_cp),
        ExtremeRecoveryScoreComponent("slottable_Champion_Point_loadout", cp_loadout.total_flat_ceiling),
        ExtremeRecoveryScoreComponent("shared_static_passives", shared_flat),
    )
    percent = (
        ExtremeRecoveryScoreComponent("Heavy Armor Constitution", constitution_percent),
        ExtremeRecoveryScoreComponent("Major Fortitude", fortitude_percent),
        ExtremeRecoveryScoreComponent("Emperor Domination", domination_percent),
        ExtremeRecoveryScoreComponent("shared_static_passive_percent", shared_percent),
    )
    score = ExtremeRecoveryFinalScoreService.compose(
        objective_key=OBJECTIVE,
        base_value=float(BASE_HEALTH_RECOVERY),
        additive_components=additive,
        percent_components=percent,
        proof_gates=tuple(gates),
    )
    unresolved.extend(score.unresolved)
    unresolved = list(dict.fromkeys(item for item in unresolved if item))

    print("EXTREME HEALTH RECOVERY FINAL RECORD CLOSURE")
    print(f"database={database}")
    print("record_kind=theoretical_stochastic_maximum")
    print("deterministic_gameplay_claim=False")
    print()
    print("BUILD / EQUIPMENT")
    print(f"race={race_name!r} racial_recovery={race_flat:.3f}")
    print(f"class_recovery={class_flat:.3f}")
    if armor:
        print(f"armor_state=7 Heavy divines:{armor[1]} invigorating:{armor[2]} recovery={armor_flat:.3f}")
    print(f"jewelry_recovery={jewelry_flat:.3f}")
    print(f"provisioning={drink.name!r} recovery={drink_flat:.3f}" if drink else "provisioning=<unresolved>")
    print(f"major_fortitude_potion_source_proven={major_fortitude_available}")
    print(f"ordinary_named_gear_recovery={ordinary_gear_flat:.3f}")
    print(f"adamant_lurker_recovery={adamant_flat:.3f}")
    if best_realization is not None:
        print(f"named_sets={tuple(zip(best_realization.set_names, best_realization.counts))!r}")
        print(f"weapon_shape={best_realization.weapon_shape.value}")
        print("destruction_staff_compatible=True")
    print()

    print("SAME-BUILD MAX MAGICKA / ENLIVENING")
    print(f"base_max_magicka={float(BASE_MAX_MAGICKA):.3f}")
    print(f"attribute_magicka={64.0 * float(MAGICKA_PER_ATTRIBUTE):.3f}")
    print(f"racial_max_magicka={race_magicka:.3f}")
    print(f"armor_glyph_max_magicka={float(armor_magicka):.3f}")
    print(f"provisioning_max_magicka_flat={provisioning_magicka_flat:.3f}")
    print(f"free_max_magicka_percent={free_magicka_percent * 100.0:.3f}")
    print(f"same_build_max_magicka={best_max_magicka:.3f}")
    print(f"enlivening_cap_reached={best_max_magicka >= 30000.0 - 1e-9}")
    for source, value, kind in best_set_magicka_sources:
        print(f"  set_magicka: {source} {kind}={value:.3f}")
    print()

    print("CHAMPION POINTS")
    print(f"non_slottable_cp_recovery={non_slottable_cp:.3f}")
    for name, value, condition in non_slottable_rows:
        print(f"  non_slottable: {name} recovery={value:.3f} condition={condition}")
    print(f"slottable_cp_recovery={cp_loadout.total_flat_ceiling:.3f}")
    for candidate in cp_loadout.selected:
        print(f"  selected: {candidate.name} recovery={candidate.flat_ceiling:.3f}")
    for candidate in cp_loadout.excluded:
        print(f"  excluded: {candidate.name} recovery={candidate.flat_ceiling:.3f}")
    for row in cp_runtime:
        print(f"  runtime: {row.candidate.name} status={row.status.value}")
    print()

    print("FINAL SCORE")
    print(f"base_health_recovery={score.base_value:.3f}")
    for row in score.additive_components:
        print(f"  additive: {row.name}={row.value:.3f}")
    print(f"pre_percent_total={score.pre_percent_total:.3f}")
    for row in score.percent_components:
        print(f"  percent: {row.name}={row.value:.3f}%")
    print(f"total_percent={score.total_percent:.3f}%")
    print(f"extreme_health_recovery_raw={score.final_value:.3f}")
    print(f"extreme_health_recovery_eso_ceil={math.ceil(score.final_value)}")
    print()

    print("PROOF GATES")
    for gate in score.proof_gates:
        print(f"  {gate.name}={gate.proven}" + (f" detail={gate.detail}" if gate.detail else ""))
    print(f"unresolved_count={len(unresolved)}")
    for item in unresolved:
        print(f"  unresolved: {item}")
    closed = score.proof_complete and not unresolved
    print(f"extreme_health_recovery_record_closed={closed}")
    if closed:
        print("NEXT_STEP=promote the closed Health Recovery theoretical maximum into the Extreme Build result/catalog surface")
        return 0
    print("NEXT_STEP=close the reported final-record proof gate before publishing the maximum")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
