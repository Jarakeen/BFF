from __future__ import annotations

"""Prove whether Oakensoul can challenge the dominant Health Recovery gear frontier.

This audit is intentionally favorable to Oakensoul. It gives the ring its full
Minor Fortitude percentage ceiling, applies no extra score penalty for one-bar
access, and uses an impossible upper bound that overcounts mutually exclusive
Recovery sources. Minor Heroism is resolved through the shared named-buff contract
against the already-reviewed Strategic Reserve baseline.
"""

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.base_character_state import BASE_HEALTH_RECOVERY
from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.gear_set_repository import GearSetRepository
from minmax.item_base_stats import ARMOR_INVIGORATING_RECOVERY_GOLD
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.mundus_repository import MundusRepository
from minmax.ultimate_generation_sources import (
    HeroismTier,
    HeroismUltimateGenerationSource,
    HeroismWindow,
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
from services.extreme_constrained_named_gear_exact_flat_search_service import (
    ExtremeNamedGearRequirement,
)
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeGearSetRecoverySpecialBranchService,
)
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
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_percent_vs_flat_dominance_service import (
    ExtremePercentVsFlatDominanceService,
)
from services.extreme_recovery_provisioning_projection_service import (
    ExtremeRecoveryProvisioningProjectionService,
)
from services.named_buff_resolution_service import (
    NamedBuffContribution,
    NamedBuffResolutionService,
)


OBJECTIVE = "health_recovery"
STRATEGIC_RESERVE_GAIN = 330.0
SCORE_SECONDS = 24.999
SURVIVOR_REQUIREMENTS = (ExtremeNamedGearRequirement("Baron Zaudrus", 2),)
_UNRESOLVED_ROW = re.compile(
    r"^(?P<name>.+?) \((?P<count>\d+)\): active set bonus is not yet mechanic-mapped: (?P<description>.*)$",
    re.DOTALL,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _special_catalog(relevance):
    rows: list[tuple[str, int, str]] = []
    unresolved: list[str] = []
    for item in relevance.unresolved:
        match = _UNRESOLVED_ROW.match(str(item))
        if match is None:
            unresolved.append(str(item))
            continue
        rows.append(
            (
                match.group("name"),
                int(match.group("count")),
                match.group("description"),
            )
        )
    catalog = ExtremeGearSetRecoverySpecialBranchService.build(tuple(rows), objective_key=OBJECTIVE)
    return catalog, tuple(dict.fromkeys((*unresolved, *catalog.unresolved)))


def _branch(catalog, name: str):
    matches = tuple(row for row in catalog.branches if row.set_name == name)
    if len(matches) != 1:
        raise RuntimeError(f"Expected one {name!r} special branch, found {len(matches)}")
    return matches[0]


def _search(*, branch, survivor: bool, topology, breakpoints, eligibility, relevance):
    requirements = [ExtremeNamedGearRequirement(branch.set_name, branch.piece_count)]
    if survivor:
        requirements.extend(SURVIVOR_REQUIREMENTS)
    return ExtremeExternalizedNamedGearConstraintSearchService.search(
        topology_catalog=topology,
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
        requirements=tuple(requirements),
        externalized=(
            ExtremeExternalizedNamedGearSemantic(branch.set_name, branch.piece_count),
        ),
    )


def _cp_flat_upper_bound(database: Path) -> tuple[float | None, tuple[str, ...]]:
    repository = ChampionPointStaticRepository(database)
    unresolved: list[str] = []
    total = 0.0

    baseline = ExtremeChampionPointObjectiveService.non_slottable_baseline_for_objective(
        repository, OBJECTIVE
    )
    for row in baseline.resolved_candidates:
        if row.reviewed_delta is not None:
            total += max(0.0, float(row.reviewed_delta))

    slottable = ExtremeChampionPointObjectiveService.slottable_candidates_for_objective(
        repository, OBJECTIVE
    )
    for row in slottable:
        if row.reviewed_delta is not None:
            total += max(0.0, float(row.reviewed_delta))

    pending = tuple(baseline.unresolved_candidates) + tuple(
        row for row in slottable if row.reviewed_delta is None
    )
    for candidate in pending:
        record = repository.get(candidate.name)
        if record is None:
            unresolved.append(f"CP upper-bound record missing: {candidate.name}")
            continue
        screening = ExtremeHealthRecoveryChampionPointScreeningService.screen(record)
        if not screening.relevant:
            continue
        branch = ExtremeHealthRecoveryChampionPointBranchService.classify(record)
        if not branch.complete or branch.flat_ceiling is None:
            unresolved.extend(
                branch.unresolved or (f"CP upper-bound branch incomplete: {candidate.name}",)
            )
            continue
        total += max(0.0, float(branch.flat_ceiling))

    return (None if unresolved else total), tuple(dict.fromkeys(unresolved))


def _prepercent_upper_bound(
    database: Path,
    *,
    structural_named_gear: float,
    provisioning,
) -> tuple[float | None, tuple[tuple[str, float], ...], tuple[str, ...]]:
    unresolved: list[str] = []
    components: list[tuple[str, float]] = [
        ("base_health_recovery", float(BASE_HEALTH_RECOVERY)),
        ("khajiit_racial_flat", 90.0),
        ("dragonknight_booming_voice_class_flat", 1950.0),
        ("oakensoul_structural_named_gear", max(0.0, float(structural_named_gear))),
    ]

    steed = ExtremeDivinesMundusObjectiveService.candidate_for_name(
        MundusRepository(database),
        "The Steed",
        OBJECTIVE,
        armor_divines_count=7,
        shield_divines=False,
    )
    if steed.projected_delta is None:
        unresolved.extend(steed.mundus.unresolved or ("Seven-Divines Steed projection unresolved",))
    else:
        components.append(
            (
                "armor_mundus_impossible_upper",
                float(steed.projected_delta) + 7.0 * float(ARMOR_INVIGORATING_RECOVERY_GOLD),
            )
        )

    jewelry = ExtremeHealthRecoveryJewelryProjectionService(
        JewelryGlyphEffectRepository(database),
        JewelryTraitRepository(database),
    ).build()
    if not jewelry.denominator_proven or jewelry.three_slot_infused_flat is None:
        unresolved.extend(jewelry.unresolved or ("Health Recovery jewelry upper bound unresolved",))
    else:
        components.append(("three_gold_infused_recovery_glyphs", float(jewelry.three_slot_infused_flat)))

    if not provisioning.comparison_proven or provisioning.food is None or provisioning.drink is None:
        unresolved.extend(provisioning.unresolved or ("Provisioning upper bound unresolved",))
    else:
        components.append(
            (
                "best_food_or_drink_recovery",
                max(float(provisioning.food.delta), float(provisioning.drink.delta)),
            )
        )

    cp_upper, cp_unresolved = _cp_flat_upper_bound(database)
    if cp_upper is None:
        unresolved.extend(cp_unresolved)
    else:
        components.append(("all_positive_cp_impossible_upper", float(cp_upper)))

    if unresolved:
        return None, tuple(components), tuple(dict.fromkeys(unresolved))
    return sum(value for _, value in components), tuple(components), ()


def _minor_heroism_resolution():
    source = HeroismUltimateGenerationSource()
    events = source.events(
        windows=(
            HeroismWindow(
                HeroismTier.MINOR,
                0.0,
                SCORE_SECONDS,
                source="reviewed Strategic Reserve baseline",
            ),
        ),
        duration_seconds=SCORE_SECONDS,
    )
    generated = sum(float(event.amount) for event in events)
    resolution = NamedBuffResolutionService.explain(
        (
            NamedBuffContribution(
                stacking_key="Minor Heroism",
                objective_key="ultimate_generation",
                projected_delta=generated,
                source="reviewed Strategic Reserve baseline",
                source_kind="runtime",
            ),
            NamedBuffContribution(
                stacking_key="Minor Heroism",
                objective_key="ultimate_generation",
                projected_delta=generated,
                source="Oakensoul Ring",
                source_kind="gear",
            ),
        ),
        objective_key="ultimate_generation",
    )
    return generated, resolution


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    repository = GearSetRepository(database)
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    raw_eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    filtered = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        database, raw_eligibility, required_armor_weight="Heavy"
    )
    catalog, semantic_unresolved = _special_catalog(relevance)
    provisioning = ExtremeRecoveryProvisioningProjectionService.build(
        database, objective_key=OBJECTIVE
    )

    print("EXTREME HEALTH RECOVERY OAKENSOUL DOMINANCE AUDIT")
    print(f"database={database}")
    print("objective=health_recovery")
    print("required_armor_weight=Heavy")
    print("one_bar_penalty_applied=False")
    print("oakensoul_minor_fortitude_credit=full_15_percent")

    if semantic_unresolved or not filtered.denominator_proven:
        for item in semantic_unresolved:
            print(f"semantic_unresolved={item}")
        for item in filtered.unresolved:
            print(f"armor_weight_unresolved={item}")
        return 2

    oak = _branch(catalog, "Oakensoul Ring")
    adamant = _branch(catalog, "Adamant Lurker")
    if oak.percent_ceiling is None or adamant.flat_ceiling is None:
        print("branch_numeric_ceiling_missing=True")
        return 2

    oak_inc = _search(
        branch=oak,
        survivor=False,
        topology=topology,
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=relevance,
    )
    oak_surv = _search(
        branch=oak,
        survivor=True,
        topology=topology,
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=relevance,
    )
    adamant_inc = _search(
        branch=adamant,
        survivor=False,
        topology=topology,
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=relevance,
    )
    adamant_surv = _search(
        branch=adamant,
        survivor=True,
        topology=topology,
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=relevance,
    )
    searches = (oak_inc, oak_surv, adamant_inc, adamant_surv)
    if any(not row.winner_found or row.search is None for row in searches):
        for label, row in zip(
            ("oakensoul_incumbent", "oakensoul_survivor", "adamant_incumbent", "adamant_survivor"),
            searches,
        ):
            if not row.winner_found or row.search is None:
                print(f"{label}_unresolved={row.unresolved!r}")
        return 2

    oak_inc_struct = float(oak_inc.search.best_exact_flat_delta or 0.0)
    oak_surv_struct = float(oak_surv.search.best_exact_flat_delta or 0.0)
    adamant_inc_score = float(adamant_inc.search.best_exact_flat_delta or 0.0) + float(adamant.flat_ceiling)
    adamant_surv_score = (
        float(adamant_surv.search.best_exact_flat_delta or 0.0)
        + float(adamant.flat_ceiling)
        + STRATEGIC_RESERVE_GAIN
    )

    incumbent_upper, incumbent_components, incumbent_unresolved = _prepercent_upper_bound(
        database,
        structural_named_gear=oak_inc_struct,
        provisioning=provisioning,
    )
    survivor_upper, survivor_components, survivor_unresolved = _prepercent_upper_bound(
        database,
        structural_named_gear=oak_surv_struct,
        provisioning=provisioning,
    )
    unresolved = tuple(dict.fromkeys((*incumbent_unresolved, *survivor_unresolved)))
    if incumbent_upper is None or survivor_upper is None or unresolved:
        for item in unresolved:
            print(f"upper_bound_unresolved={item}")
        return 2

    incumbent_displaced = max(0.0, adamant_inc_score - oak_inc_struct)
    survivor_base = oak_surv_struct + STRATEGIC_RESERVE_GAIN
    survivor_displaced = max(0.0, adamant_surv_score - survivor_base)
    incumbent_dominance = ExtremePercentVsFlatDominanceService.assess(
        pre_percent_subtotal_upper_bound=incumbent_upper,
        percent_ceiling=float(oak.percent_ceiling),
        displaced_flat_value=incumbent_displaced,
    )
    survivor_dominance = ExtremePercentVsFlatDominanceService.assess(
        pre_percent_subtotal_upper_bound=survivor_upper,
        percent_ceiling=float(oak.percent_ceiling),
        displaced_flat_value=survivor_displaced,
    )

    minor_heroism_generated, heroism_resolution = _minor_heroism_resolution()
    heroism_redundant = len(heroism_resolution.selected) == 1 and len(heroism_resolution.suppressed) == 1

    print(f"minor_heroism_generation_over_window={minor_heroism_generated:.3f}")
    print(f"minor_heroism_selected_sources={tuple(row.source for row in heroism_resolution.selected)!r}")
    print(f"minor_heroism_suppressed_sources={tuple(row.suppressed_source for row in heroism_resolution.suppressed)!r}")
    print(f"oakensoul_minor_heroism_redundant={heroism_redundant}")
    print(f"adamant_incumbent_frontier={adamant_inc_score:.3f}")
    print(f"adamant_survivor_frontier={adamant_surv_score:.3f}")
    print(f"oakensoul_incumbent_structural={oak_inc_struct:.3f}")
    print(f"oakensoul_survivor_structural={oak_surv_struct:.3f}")
    print(
        "oakensoul_incumbent_prepercent_upper_components="
        + repr(tuple((name, round(value, 3)) for name, value in incumbent_components))
    )
    print(
        "oakensoul_survivor_prepercent_upper_components="
        + repr(tuple((name, round(value, 3)) for name, value in survivor_components))
    )
    print(
        f"oakensoul_incumbent_percent_gain_upper={incumbent_dominance.percent_gain_upper_bound:.3f} "
        f"required_gain={incumbent_dominance.displaced_flat_value:.3f} "
        f"dominated={incumbent_dominance.dominated}"
    )
    print(
        f"oakensoul_survivor_percent_gain_upper={survivor_dominance.percent_gain_upper_bound:.3f} "
        f"required_gain={survivor_dominance.displaced_flat_value:.3f} "
        f"dominated={survivor_dominance.dominated}"
    )

    dominated = bool(
        heroism_redundant
        and incumbent_dominance.dominated
        and survivor_dominance.dominated
    )
    print(f"oakensoul_dominated={dominated}")
    if not dominated:
        print("NEXT_STEP=explicitly rescore Oakensoul one-bar runtime/search state")
        return 2
    print("NEXT_STEP=close Baron Zaudrus action volume and Decisive stochastic/numeric Ultimate legality")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
