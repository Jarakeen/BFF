from __future__ import annotations

"""Compose the closed Extreme Health Recovery proof frontier into one final record.

Prerequisites are the already-reviewed special-set dominance audits and the stochastic
Baron Zaudrus + Decisive Ultimate-refill witness.  This audit re-resolves every numeric
component that can still affect the final score, requires a Destruction-Staff-compatible
named-gear witness, scores Enlivening Overflow from same-build Max Magicka, and then
uses the shared Recovery final-score composer.
"""

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.armor_glyph_repository import ArmorGlyphEffectRepository
from minmax.base_character_state import BASE_HEALTH_RECOVERY, BASE_MAX_MAGICKA, MAGICKA_PER_ATTRIBUTE
from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.effects import EffectOperation, EffectUnit
from minmax.gear_set_effect_service import GearSetEffectService
from minmax.gear_set_repository import GearSetRepository
from minmax.item_base_stats import ARMOR_INVIGORATING_RECOVERY_GOLD
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.mundus_repository import MundusRepository
from minmax.named_combat_buffs import effects_for_buff
from minmax.passive_math import (
    heavy_armor_constitution_health_recovery_percent,
    mages_guild_magicka_controller_percent,
    undaunted_mettle_resource_percent,
)
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from minmax.race_repository import RaceRepository
from minmax.stat_ids import StatId
from minmax.ultimate_resource_timeline import UltimateGenerationEvent
from services.champion_point_loadout_service import (
    ChampionPointLoadoutCandidate,
    ChampionPointLoadoutService,
)
from services.extreme_armor_weight_filtered_slot_eligibility_service import (
    ExtremeArmorWeightFilteredSlotEligibilityService,
)
from services.extreme_champion_point_objective_service import ExtremeChampionPointObjectiveService
from services.extreme_divines_mundus_objective_service import ExtremeDivinesMundusObjectiveService
from services.extreme_externalized_named_gear_constraint_search_service import (
    ExtremeExternalizedNamedGearConstraintSearchService,
    ExtremeExternalizedNamedGearSemantic,
)
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeGearSetRecoverySpecialBranchService,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_heal_class_route_service import ExtremeHealClassRouteService
from services.extreme_health_recovery_champion_point_branch_service import (
    ExtremeHealthRecoveryChampionPointBranchService,
)
from services.extreme_health_recovery_class_route_ceiling_service import (
    ExtremeHealthRecoveryClassRouteCeilingService,
)
from services.extreme_health_recovery_class_route_signature_service import (
    ExtremeHealthRecoveryClassRouteSignatureService,
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
from services.extreme_recovery_provisioning_projection_service import (
    ExtremeRecoveryProvisioningProjectionService,
)
from services.extreme_skill_universe_service import ExtremeSkillDomain, ExtremeSkillUniverseService
from services.extreme_constrained_named_gear_exact_flat_search_service import ExtremeNamedGearRequirement
from services.skill_choice_service import load_skill_choices


OBJECTIVE = "health_recovery"
DESTRO_TYPES = frozenset({"Inferno Staff", "Ice Staff", "Lightning Staff"})
_UNRESOLVED_ROW = re.compile(
    r"^(?P<name>.+?) \((?P<count>\d+)\): active set bonus is not yet mechanic-mapped: (?P<description>.*)$",
    re.DOTALL,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _soldier_slot_ceiling(database: Path) -> int:
    rows = [
        row
        for row in load_skill_choices(database)
        if " ".join(str(row.get("skill_line") or "").strip().casefold().split()) == "soldier of apocrypha"
        and int(row.get("is_player") or 0) == 1
        and int(row.get("is_passive") or 0) == 0
    ]
    regular = {
        int(row.get("base_ability_id") or row.get("ability_id") or 0)
        for row in rows
        if int(row.get("base_mechanic") or 0) != 8
    }
    ultimate = {
        int(row.get("base_ability_id") or row.get("ability_id") or 0)
        for row in rows
        if int(row.get("base_mechanic") or 0) == 8
    }
    regular.discard(0)
    ultimate.discard(0)
    return min(5, len(regular)) + min(1, len(ultimate))


def _race_witness(database: Path):
    rows = []
    unresolved_mentions = []
    for passive in ExtremeSkillUniverseService(database).all_player_skills():
        if not passive.is_passive or passive.domain is not ExtremeSkillDomain.RACIAL:
            continue
        projection = ExtremePassiveProjectionService.project(passive)
        contributions = tuple(row for row in projection.contributions if row.objective_key == OBJECTIVE)
        if contributions:
            flat = sum(float(row.flat) for row in contributions)
            percent = sum(float(row.percent_of_reference) for row in contributions)
            if flat > 0.0 or percent > 0.0:
                rows.append((flat, percent, passive))
            continue
        text = f"{passive.name} {passive.description}".casefold()
        if "health recovery" in text or (
            "health" in text and "magicka" in text and "stamina recovery" in text
        ):
            unresolved_mentions.append(passive.name)
    rows.sort(key=lambda item: (-item[0], -item[1], item[2].skill_line.casefold()))
    return (rows[0] if rows else None), tuple(unresolved_mentions), tuple(rows)


def _class_witness(database: Path):
    routes = ExtremeHealClassRouteService().all_routes()
    signatures = ExtremeHealthRecoveryClassRouteSignatureService.build(routes)
    ceilings = ExtremeHealthRecoveryClassRouteCeilingService.build(
        signatures,
        wellspring_slot_ceiling=_soldier_slot_ceiling(database),
    )
    return ceilings.best_complete, ceilings.unresolved_rows


def _armor_witness(database: Path):
    rows = []
    repository = MundusRepository(database)
    for divines_count in range(8):
        invigorating_count = 7 - divines_count
        mundus = ExtremeDivinesMundusObjectiveService.candidate_for_name(
            repository,
            "The Steed",
            OBJECTIVE,
            armor_divines_count=divines_count,
            shield_divines=False,
        )
        if mundus.projected_delta is None:
            continue
        invigorating = invigorating_count * float(ARMOR_INVIGORATING_RECOVERY_GOLD)
        total = float(mundus.projected_delta) + invigorating
        rows.append((total, divines_count, invigorating_count, float(mundus.projected_delta), invigorating))
    rows.sort(key=lambda row: (-row[0], -row[1]))
    return rows[0] if rows else None


def _special_catalog(relevance):
    rows = []
    unresolved = []
    for item in relevance.unresolved:
        match = _UNRESOLVED_ROW.match(str(item))
        if match is None:
            unresolved.append(str(item))
            continue
        rows.append((match.group("name"), int(match.group("count")), match.group("description")))
    catalog = ExtremeGearSetRecoverySpecialBranchService.build(tuple(rows), objective_key=OBJECTIVE)
    return catalog, tuple(dict.fromkeys((*unresolved, *catalog.unresolved)))


def _destro_compatible(realization, eligibility_by_id) -> bool:
    weapons = realization.weapon_assignments
    if not weapons:
        return True
    if len(weapons) != 1:
        return False
    row = eligibility_by_id.get(int(weapons[0].set_id))
    return bool(row and DESTRO_TYPES.intersection(set(row.weapon_types)))


def _percent_decimal(effect) -> float:
    value = float(effect.value)
    return value / 100.0 if effect.unit is EffectUnit.PERCENT else value


def _set_magicka_effects(repository: GearSetRepository, realization):
    service = GearSetEffectService(repository)
    flat = 0.0
    percent = 0.0
    sources = []
    for set_id, count in zip(realization.set_ids, realization.counts):
        for effect in service.resolve_effects(int(set_id), int(count)):
            if effect.stat is not StatId.MAX_MAGICKA:
                continue
            if effect.operation is EffectOperation.ADD:
                flat += float(effect.value)
                sources.append((effect.source, float(effect.value), "flat"))
            elif effect.operation is EffectOperation.ADD_PERCENT:
                value = _percent_decimal(effect)
                percent += value
                sources.append((effect.source, value, "percent"))
    return flat, percent, tuple(sources)


def _armor_magicka_glyph_flat(database: Path) -> float | None:
    effects = ArmorGlyphEffectRepository(database).get_armor_glyph_effect_by_name(
        "Glyph of Magicka", use_max_value=True
    )
    values = [
        float(row.value)
        for row in effects
        if row.stat is StatId.MAX_MAGICKA and row.operation is EffectOperation.ADD
    ]
    if not values:
        return None
    base = max(values)
    return base * (3.0 + 4.0 * 0.4)


def _provisioning_magicka(database: Path, name: str):
    effects, unresolved = ProvisioningStaticRepository(database).resolve(name)
    flat = 0.0
    percent = 0.0
    for effect in effects:
        if effect.stat is not StatId.MAX_MAGICKA:
            continue
        if effect.operation is EffectOperation.ADD:
            flat += float(effect.value)
        elif effect.operation is EffectOperation.ADD_PERCENT:
            percent += _percent_decimal(effect)
    return flat, percent, tuple(unresolved)


def _cp_candidates(database: Path, *, max_magicka: float):
    repository = ChampionPointStaticRepository(database)
    rows = []
    unresolved = []
    for name in (
        "Strategic Reserve",
        "Peace of Mind",
        "Enlivening Overflow",
        "Sustained by Suffering",
        "Rejuvenation",
    ):
        record = repository.get(name)
        if record is None:
            unresolved.append(f"selected CP record missing: {name}")
            continue
        if name == "Rejuvenation":
            candidate = ExtremeChampionPointObjectiveService.candidate_for_record(repository, record, OBJECTIVE)
            if candidate.reviewed_delta is None:
                unresolved.extend(candidate.unresolved or (f"{name}: numeric value unresolved",))
                continue
            value = float(candidate.reviewed_delta)
            condition = None
        else:
            branch = ExtremeHealthRecoveryChampionPointBranchService.classify(record)
            if not branch.complete or branch.flat_ceiling is None:
                unresolved.extend(branch.unresolved or (f"{name}: branch unresolved",))
                continue
            value = float(branch.flat_ceiling)
            condition = branch.condition
            if name == "Enlivening Overflow":
                value = min(value, max(0.0, float(max_magicka)) * 0.005)
        rows.append(
            ChampionPointLoadoutCandidate(
                name=name,
                discipline_index=record.discipline_index,
                flat_ceiling=value,
                condition=condition,
            )
        )
    loadout = ChampionPointLoadoutService.build(tuple(rows))
    return loadout, tuple(unresolved)


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    unresolved = []
    gates = []

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
    requirements = (
        ExtremeNamedGearRequirement("Adamant Lurker", 5),
        ExtremeNamedGearRequirement("Baron Zaudrus", 2),
    )
    externalized = (
        ExtremeExternalizedNamedGearSemantic("Adamant Lurker", 5),
    )
    gear_search = ExtremeExternalizedNamedGearConstraintSearchService.search(
        topology_catalog=topology,
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=relevance,
        requirements=requirements,
        externalized=externalized,
    )
    eligibility_by_id = {int(row.set_id): row for row in filtered.catalog.sets}
    realizations = () if gear_search.search is None else gear_search.search.realizations
    destro_realizations = tuple(row for row in realizations if _destro_compatible(row, eligibility_by_id))
    ordinary_gear_flat = float(gear_search.search.best_exact_flat_delta or 0.0) if gear_search.search else 0.0
    adamant_flat = float(adamant.flat_ceiling or 0.0) if adamant else 0.0
    adamant_compatible = bool(
        adamant
        and ExtremeHealthRecoveryRuntimeCompatibilityService.assess(
            adamant, ExtremeHealthRecoveryRuntimeState()
        ).status is ExtremeHealthRecoveryCompatibility.COMPATIBLE
    )
    gates.extend(
        (
            ExtremeRecoveryProofGate("heavy_named_gear_search", filtered.denominator_proven and gear_search.winner_found),
            ExtremeRecoveryProofGate("adamant_runtime", adamant_compatible),
            ExtremeRecoveryProofGate("destruction_staff_realization", bool(destro_realizations)),
        )
    )
    unresolved.extend(special_unresolved)
    unresolved.extend(gear_search.unresolved)

    # Max Magicka is a secondary proof variable used only to score Enlivening Overflow.
    # Choose the Destro-compatible Health-Recovery-tied realization with the strongest
    # otherwise-compatible Max Magicka set contribution.
    race_map = RaceRepository(database).get_stat_map_by_name(race_name) if race_name else {}
    race_magicka = float(race_map.get("max_magicka", 0.0))
    armor_glyph_flat = _armor_magicka_glyph_flat(database)
    if armor_glyph_flat is None:
        unresolved.append("canonical Max Magicka armor glyph value unresolved")
        armor_glyph_flat = 0.0

    provision_magicka_flat = provision_magicka_percent = 0.0
    if drink is not None:
        provision_magicka_flat, provision_magicka_percent, provision_unresolved = _provisioning_magicka(database, drink.name)
        unresolved.extend(provision_unresolved)

    best_realization = None
    best_max_magicka = -1.0
    best_magicka_sources = ()
    for realization in destro_realizations:
        set_flat, set_percent, set_sources = _set_magicka_effects(gear_repository, realization)
        # Five active regular slots are needed for Force Shock, one Earthen Heart
        # trigger, and three Mages Guild skills. The Destro Ultimate occupies the
        # Ultimate slot and supplies the reviewed 250-Ultimate Booming Voice cast.
        free_percent = (
            undaunted_mettle_resource_percent(1)
            + mages_guild_magicka_controller_percent(3)
        )
        pre_percent_magicka = (
            float(BASE_MAX_MAGICKA)
            + 64.0 * float(MAGICKA_PER_ATTRIBUTE)
            + race_magicka
            + float(armor_glyph_flat)
            + provision_magicka_flat
            + set_flat
        )
        max_magicka = pre_percent_magicka * (
            1.0 + free_percent + provision_magicka_percent + set_percent
        )
        if max_magicka > best_max_magicka + 1e-9:
            best_max_magicka = max_magicka
            best_realization = realization
            best_magicka_sources = set_sources

    if best_realization is None:
        best_max_magicka = 0.0
    gates.append(ExtremeRecoveryProofGate("same_build_max_magicka_witness", best_realization is not None))

    cp_loadout, cp_unresolved = _cp_candidates(database, max_magicka=best_max_magicka)
    unresolved.extend(cp_unresolved)
    # The stochastic refill audit already proves enough post-cast generation to
    # return to 500. Represent only that proven composite here; this layer does not
    # re-own Baron/Decisive mechanics.
    state = ExtremeHealthRecoveryRuntimeState(
        max_magicka=best_max_magicka,
        ultimate_generation_events=(
            UltimateGenerationEvent(24.0, 250.0, "proven Baron+Decisive+baseline refill composite"),
        ),
    )
    cp_runtime = ExtremeHealthRecoveryRuntimeCompatibilityService.assess_champion_points(
        cp_loadout.selected, state
    )
    cp_runtime_compatible = all(
        row.status is ExtremeHealthRecoveryCompatibility.COMPATIBLE for row in cp_runtime
    )
    gates.extend(
        (
            ExtremeRecoveryProofGate("cp_loadout_legality", cp_loadout.denominator_proven),
            ExtremeRecoveryProofGate("cp_runtime_compatibility", cp_runtime_compatible),
            ExtremeRecoveryProofGate(
                "stochastic_ultimate_refill_checkpoint",
                True,
                "Closed by Force Shock/Baron + Decisive all-procs witness audit.",
            ),
            ExtremeRecoveryProofGate(
                "special_named_gear_frontier_checkpoint",
                True,
                "Closed by constrained-special, Willow, and Oakensoul dominance audits.",
            ),
        )
    )
    for row in cp_runtime:
        if row.status is not ExtremeHealthRecoveryCompatibility.COMPATIBLE:
            unresolved.append(f"{row.candidate.name}: {row.reason}")

    # Shared recovery percentages that coexist at the scoring instant.
    constitution_percent = heavy_armor_constitution_health_recovery_percent(7) * 100.0
    fortitude_effects = tuple(
        row for row in effects_for_buff("Major Fortitude") if row.stat is StatId.HEALTH_RECOVERY
    )
    fortitude_percent = (
        float(fortitude_effects[0].value) * 100.0 if len(fortitude_effects) == 1 else 0.0
    )
    gates.append(ExtremeRecoveryProofGate("major_fortitude_semantics", len(fortitude_effects) == 1))

    domination = None
    for passive in ExtremeSkillUniverseService(database).all_player_skills():
        if not passive.is_passive or passive.name.casefold() != "domination":
            continue
        branch = ExtremeHealthRecoveryPassiveSpecialBranchService.classify(passive)
        if branch is not None and branch.percent_ceiling is not None:
            domination = branch
            break
    domination_percent = float(domination.percent_ceiling or 0.0) if domination else 0.0
    gates.append(
        ExtremeRecoveryProofGate(
            "emperor_domination_six_home_keeps",
            bool(domination and domination.can_raise_self and domination_percent > 0.0),
        )
    )

    # Include any simple unconditional shared passive Health Recovery that is not
    # racial or class-owned. Contextual Constitution and Domination remain separate.
    shared_flat = 0.0
    shared_percent = 0.0
    shared_sources = []
    for passive in ExtremeSkillUniverseService(database).all_player_skills():
        if not passive.is_passive or passive.domain in {ExtremeSkillDomain.RACIAL, ExtremeSkillDomain.CLASS}:
            continue
        projection = ExtremePassiveProjectionService.project(passive)
        for row in projection.contributions:
            if row.objective_key != OBJECTIVE:
                continue
            shared_flat += float(row.flat)
            shared_percent += float(row.percent_of_reference) * 100.0
            shared_sources.append(row.source)

    additive = (
        ExtremeRecoveryScoreComponent(f"racial:{race_name or '<unresolved>'}", race_flat),
        ExtremeRecoveryScoreComponent("class_route", class_flat),
        ExtremeRecoveryScoreComponent("armor_mundus_traits", armor_flat),
        ExtremeRecoveryScoreComponent("three_infused_jewelry_recovery_glyphs", jewelry_flat),
        ExtremeRecoveryScoreComponent(f"drink:{drink.name if drink else '<unresolved>'}", drink_flat),
        ExtremeRecoveryScoreComponent("ordinary_named_gear", ordinary_gear_flat),
        ExtremeRecoveryScoreComponent("Adamant Lurker 5pc", adamant_flat),
        ExtremeRecoveryScoreComponent("Champion Point loadout", cp_loadout.total_flat_ceiling),
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

    print("EXTREME HEALTH RECOVERY FINAL RECORD AUDIT")
    print(f"database={database}")
    print("record_kind=theoretical_stochastic_maximum")
    print("deterministic_gameplay_claim=False")
    print()
    print("BUILD WITNESS")
    print(f"race={race_name!r} racial_health_recovery={race_flat:.3f}")
    print(f"class_flat={class_flat:.3f}")
    if armor:
        print(
            f"armor_state=7 Heavy divines:{armor[1]} invigorating:{armor[2]} "
            f"steed={armor[3]:.3f} invigorating_flat={armor[4]:.3f} recovery={armor[0]:.3f}"
        )
    print(f"jewelry_recovery={jewelry_flat:.3f}")
    print(f"provisioning={drink.name!r} recovery={drink_flat:.3f}" if drink else "provisioning=<unresolved>")
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
    print(f"armor_glyph_max_magicka={float(armor_glyph_flat):.3f}")
    print(f"provisioning_max_magicka_flat={provision_magicka_flat:.3f}")
    print(f"provisioning_max_magicka_percent={provision_magicka_percent * 100.0:.3f}")
    print(f"same_build_max_magicka={best_max_magicka:.3f}")
    print(f"enlivening_cap_reached={best_max_magicka >= 30000.0 - 1e-9}")
    for source, value, kind in best_magicka_sources:
        print(f"  set_magicka: {source} {kind}={value:.3f}")
    print()

    print("CHAMPION POINT LOADOUT")
    print(f"cp_total_flat={cp_loadout.total_flat_ceiling:.3f}")
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
    print(f"extreme_health_recovery_eso_ceil={int(-(-score.final_value // 1)))}")
    print()

    print("PROOF GATES")
    for gate in score.proof_gates:
        print(f"  {gate.name}={gate.proven}" + (f" detail={gate.detail}" if gate.detail else ""))
    print(f"unresolved_count={len(unresolved)}")
    for item in unresolved:
        print(f"  unresolved: {item}")
    final_closed = score.proof_complete and not unresolved
    print(f"extreme_health_recovery_record_closed={final_closed}")
    if final_closed:
        print("NEXT_STEP=promote the closed Health Recovery record into the Extreme Build result/catalog surface")
        return 0
    print("NEXT_STEP=close the reported final-record proof gate before publishing the maximum")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
