from __future__ import annotations

"""Compose reviewed Health Recovery special gear with the surviving Ultimate route.

The ordinary exact-flat audit leaves one positive Ultimate challenger:
Baron Zaudrus + Decisive. This diagnostic compares the best seven-Heavy incumbent
and that challenger across the same classified recovery-special named-set frontier.

Flat-compatible branches are composed directly. Formula and percentage branches
with safe numeric ceilings are proof-pruned when even those ceilings cannot catch the
existing frontier. Alternate provisioning branches use the shared canonical Recovery
provisioning projection. Search-state branches remain explicit proof obligations.
"""

import argparse
from dataclasses import dataclass
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
from services.extreme_armor_weight_filtered_slot_eligibility_service import (
    ExtremeArmorWeightFilteredSlotEligibilityService,
)
from services.extreme_champion_point_objective_service import ExtremeChampionPointObjectiveService
from services.extreme_constrained_named_gear_exact_flat_search_service import (
    ExtremeConstrainedNamedGearExactFlatSearchService,
    ExtremeNamedGearRequirement,
)
from services.extreme_divines_mundus_objective_service import ExtremeDivinesMundusObjectiveService
from services.extreme_externalized_named_gear_constraint_search_service import (
    ExtremeExternalizedNamedGearConstraintSearchService,
    ExtremeExternalizedNamedGearSemantic,
)
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeGearSetRecoverySpecialBranchService,
    ExtremeRecoverySpecialBranch,
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
from services.extreme_health_recovery_runtime_compatibility_service import (
    ExtremeHealthRecoveryCompatibility,
    ExtremeHealthRecoveryRuntimeCompatibilityService,
    ExtremeHealthRecoveryRuntimeState,
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


OBJECTIVE = "health_recovery"
STRATEGIC_RESERVE_GAIN = 330.0
SURVIVOR_REQUIREMENTS = (ExtremeNamedGearRequirement("Baron Zaudrus", 2),)
_UNRESOLVED_ROW = re.compile(
    r"^(?P<name>.+?) \((?P<count>\d+)\): active set bonus is not yet mechanic-mapped: (?P<description>.*)$",
    re.DOTALL,
)


@dataclass(frozen=True)
class _ScoredBranch:
    branch: ExtremeRecoverySpecialBranch | None
    incumbent_score: float
    survivor_score: float

    @property
    def survivor_margin(self) -> float:
        return self.survivor_score - self.incumbent_score


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _special_catalog(relevance):
    rows: list[tuple[str, int, str]] = []
    parse_unresolved: list[str] = []
    for item in relevance.unresolved:
        match = _UNRESOLVED_ROW.match(str(item))
        if match is None:
            parse_unresolved.append(str(item))
            continue
        rows.append(
            (
                match.group("name"),
                int(match.group("count")),
                match.group("description"),
            )
        )
    catalog = ExtremeGearSetRecoverySpecialBranchService.build(
        tuple(rows), objective_key=OBJECTIVE
    )
    unresolved = tuple(dict.fromkeys((*parse_unresolved, *catalog.unresolved)))
    return catalog, unresolved


def _externalized_search(
    *,
    branch: ExtremeRecoverySpecialBranch,
    survivor: bool,
    topology,
    breakpoints,
    eligibility,
    relevance,
):
    external = ExtremeExternalizedNamedGearSemantic(
        branch.set_name,
        branch.piece_count,
    )
    requirements = [
        ExtremeNamedGearRequirement(branch.set_name, branch.piece_count),
    ]
    if survivor:
        requirements.extend(SURVIVOR_REQUIREMENTS)
    return ExtremeExternalizedNamedGearConstraintSearchService.search(
        topology_catalog=topology,
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
        requirements=tuple(requirements),
        externalized=(external,),
    )


def _best_scores(scored: list[_ScoredBranch]) -> tuple[float, float]:
    return (
        max(row.incumbent_score for row in scored),
        max(row.survivor_score for row in scored),
    )


def _structural_reason(branch: ExtremeRecoverySpecialBranch, *, survivor: bool) -> str:
    if survivor and branch.piece_count == 2:
        return (
            "no legal shared 2pc witness with required Baron Zaudrus 2pc under the "
            "current topology/slot eligibility; the constrained 2pc allocations compete"
        )
    return "no legal constrained physical witness under the current topology/slot eligibility"


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
    baseline_pending = baseline.unresolved_candidates

    slottable = ExtremeChampionPointObjectiveService.slottable_candidates_for_objective(
        repository, OBJECTIVE
    )
    slottable_pending = tuple(row for row in slottable if row.reviewed_delta is None)
    for row in slottable:
        if row.reviewed_delta is not None:
            total += max(0.0, float(row.reviewed_delta))

    for candidate in (*baseline_pending, *slottable_pending):
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
                branch.unresolved
                or (f"CP upper-bound branch incomplete: {candidate.name}",)
            )
            continue
        total += max(0.0, float(branch.flat_ceiling))

    return (None if unresolved else total), tuple(dict.fromkeys(unresolved))


def _willow_prepercent_upper_bound(
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
        ("willow_structural_named_gear", max(0.0, float(structural_named_gear))),
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
        # Deliberately impossible overcount: allow seven Divines and seven Invigorating
        # armor traits simultaneously. This is safe for an upper-bound dominance proof.
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


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    repository = GearSetRepository(database)
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    raw_eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    filtered = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        database,
        raw_eligibility,
        required_armor_weight="Heavy",
    )
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(
        OBJECTIVE,
        breakpoints,
    )
    catalog, semantic_unresolved = _special_catalog(relevance)
    provisioning = ExtremeRecoveryProvisioningProjectionService.build(
        database,
        objective_key=OBJECTIVE,
    )

    print("EXTREME HEALTH RECOVERY SPECIAL CONSTRAINED ROUTE AUDIT")
    print(f"database={database}")
    print("objective=health_recovery")
    print("required_armor_weight=Heavy")
    print("ultimate_survivor=('baron_zaudrus', 'decisive')")
    print(f"armor_weight_filter_denominator_proven={filtered.denominator_proven}")
    print(f"classified_special_branches={len(catalog.branches)}")
    print(f"positive_special_challengers={len(catalog.positive_challengers)}")
    print(f"special_semantic_unresolved={len(semantic_unresolved)}")
    print(f"provisioning_comparison_proven={provisioning.comparison_proven}")
    if provisioning.food is not None:
        print(
            f"best_food={provisioning.food.name!r} "
            f"health_recovery_delta={provisioning.food.delta:.3f}"
        )
    if provisioning.drink is not None:
        print(
            f"best_drink={provisioning.drink.name!r} "
            f"health_recovery_delta={provisioning.drink.delta:.3f}"
        )

    if not filtered.denominator_proven or semantic_unresolved:
        for item in filtered.unresolved:
            print(f"  armor_weight_unresolved={item}")
        for item in semantic_unresolved:
            print(f"  special_unresolved={item}")
        print("NEXT_STEP=close armor-weight or recovery-special semantic evidence")
        return 2

    incumbent = ExtremeConstrainedNamedGearExactFlatSearchService(
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=relevance,
        requirements=(),
    ).search(topology)
    survivor = ExtremeConstrainedNamedGearExactFlatSearchService(
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=relevance,
        requirements=SURVIVOR_REQUIREMENTS,
    ).search(topology)
    if incumbent.best_exact_flat_delta is None or survivor.best_exact_flat_delta is None:
        print(f"incumbent_unresolved={incumbent.unresolved!r}")
        print(f"survivor_unresolved={survivor.unresolved!r}")
        print("NEXT_STEP=close ordinary constrained branch before special composition")
        return 2

    base_incumbent = float(incumbent.best_exact_flat_delta)
    base_survivor = float(survivor.best_exact_flat_delta) + STRATEGIC_RESERVE_GAIN
    scored: list[_ScoredBranch] = [
        _ScoredBranch(None, base_incumbent, base_survivor)
    ]
    pending: list[str] = []
    pruned: list[str] = []
    state = ExtremeHealthRecoveryRuntimeState()

    print()
    print("BASE EXACT-FLAT COMPARISON")
    print(f"incumbent_effective_score={base_incumbent:.3f}")
    print(
        f"baron_decisive_effective_score={base_survivor:.3f} "
        f"margin={base_survivor - base_incumbent:.3f}"
    )
    print()
    print("SPECIAL BRANCH COMPOSITION")

    for branch in catalog.positive_challengers:
        compatibility = ExtremeHealthRecoveryRuntimeCompatibilityService.assess(branch, state)
        label = f"{branch.set_name} {branch.piece_count}pc"
        if compatibility.status in {
            ExtremeHealthRecoveryCompatibility.INCOMPATIBLE,
            ExtremeHealthRecoveryCompatibility.REDUNDANT_NAMED_BUFF,
        }:
            pruned.append(label)
            print(
                f"  pruned: {label} kind={branch.kind.value} "
                f"status={compatibility.status.value} reason={compatibility.reason}"
            )
            continue

        incumbent_search = _externalized_search(
            branch=branch,
            survivor=False,
            topology=topology,
            breakpoints=breakpoints,
            eligibility=filtered.catalog,
            relevance=relevance,
        )
        survivor_search = _externalized_search(
            branch=branch,
            survivor=True,
            topology=topology,
            breakpoints=breakpoints,
            eligibility=filtered.catalog,
            relevance=relevance,
        )
        if not incumbent_search.winner_found or incumbent_search.search is None:
            reason = incumbent_search.unresolved or (_structural_reason(branch, survivor=False),)
            print(
                f"  structurally_unavailable_incumbent: {label} reasons={reason!r}"
            )
            continue
        if not survivor_search.winner_found or survivor_search.search is None:
            reason = survivor_search.unresolved or (_structural_reason(branch, survivor=True),)
            print(
                f"  structurally_unavailable_survivor: {label} reasons={reason!r}"
            )
            continue

        incumbent_ordinary = float(incumbent_search.search.best_exact_flat_delta or 0.0)
        survivor_ordinary = float(survivor_search.search.best_exact_flat_delta or 0.0)

        directly_composable = (
            compatibility.status is ExtremeHealthRecoveryCompatibility.COMPATIBLE
            and branch.flat_ceiling is not None
            and branch.percent_ceiling is None
            and not branch.search_state_rule
        )
        if directly_composable:
            special = float(branch.flat_ceiling)
            incumbent_effective = incumbent_ordinary + special
            survivor_effective = survivor_ordinary + special + STRATEGIC_RESERVE_GAIN
            scored.append(
                _ScoredBranch(branch, incumbent_effective, survivor_effective)
            )
            print(
                f"  scored: {label} kind={branch.kind.value} special_flat={special:.3f} "
                f"incumbent_ordinary={incumbent_ordinary:.3f} "
                f"incumbent_effective={incumbent_effective:.3f} "
                f"survivor_ordinary={survivor_ordinary:.3f} "
                f"survivor_effective={survivor_effective:.3f} "
                f"survivor_margin_same_branch={survivor_effective - incumbent_effective:.3f}"
            )
            continue

        if (
            compatibility.status is ExtremeHealthRecoveryCompatibility.NUMERIC_EQUIPMENT_PROOF
            and branch.flat_ceiling is not None
            and branch.percent_ceiling is None
        ):
            incumbent_ceiling = incumbent_ordinary + float(branch.flat_ceiling)
            survivor_ceiling = survivor_ordinary + float(branch.flat_ceiling) + STRATEGIC_RESERVE_GAIN
            best_incumbent_so_far, best_survivor_so_far = _best_scores(scored)
            if (
                incumbent_ceiling <= best_incumbent_so_far + 1e-9
                and survivor_ceiling <= best_survivor_so_far + 1e-9
            ):
                pruned.append(label)
                print(
                    f"  ceiling_pruned: {label} kind={branch.kind.value} "
                    f"incumbent_ceiling={incumbent_ceiling:.3f} "
                    f"best_incumbent={best_incumbent_so_far:.3f} "
                    f"survivor_ceiling={survivor_ceiling:.3f} "
                    f"best_survivor={best_survivor_so_far:.3f}"
                )
                continue

        if (
            branch.set_name == "Green Pact"
            and compatibility.status is ExtremeHealthRecoveryCompatibility.ALTERNATE_PROVISIONING
            and branch.flat_ceiling is not None
            and provisioning.comparison_proven
            and provisioning.food is not None
            and provisioning.drink is not None
        ):
            provisioning_adjustment = provisioning.food.delta - provisioning.drink.delta
            special = float(branch.flat_ceiling)
            incumbent_effective = incumbent_ordinary + special + provisioning_adjustment
            survivor_effective = (
                survivor_ordinary
                + special
                + provisioning_adjustment
                + STRATEGIC_RESERVE_GAIN
            )
            scored.append(_ScoredBranch(branch, incumbent_effective, survivor_effective))
            print(
                f"  scored_alternate_provisioning: {label} special_flat={special:.3f} "
                f"food_minus_drink={provisioning_adjustment:.3f} "
                f"incumbent_effective={incumbent_effective:.3f} "
                f"survivor_effective={survivor_effective:.3f} "
                f"survivor_margin_same_branch={survivor_effective - incumbent_effective:.3f}"
            )
            continue

        if branch.set_name == "Willow's Path" and branch.percent_ceiling is not None:
            best_incumbent_so_far, best_survivor_so_far = _best_scores(scored)
            displaced_incumbent = max(0.0, best_incumbent_so_far - incumbent_ordinary)
            displaced_survivor = max(
                0.0,
                best_survivor_so_far - (survivor_ordinary + STRATEGIC_RESERVE_GAIN),
            )
            displaced_flat = min(displaced_incumbent, displaced_survivor)
            subtotal_upper, components, willow_unresolved = _willow_prepercent_upper_bound(
                database,
                structural_named_gear=max(incumbent_ordinary, survivor_ordinary),
                provisioning=provisioning,
            )
            if subtotal_upper is not None and not willow_unresolved:
                dominance = ExtremePercentVsFlatDominanceService.assess(
                    pre_percent_subtotal_upper_bound=subtotal_upper,
                    percent_ceiling=float(branch.percent_ceiling),
                    displaced_flat_value=displaced_flat,
                )
                print(
                    "  willow_prepercent_upper_components="
                    + repr(tuple((name, round(value, 3)) for name, value in components))
                )
                if dominance.dominated:
                    pruned.append(label)
                    print(
                        f"  percent_ceiling_pruned: {label} "
                        f"pre_percent_subtotal_upper={dominance.pre_percent_subtotal_upper_bound:.3f} "
                        f"percent_gain_upper={dominance.percent_gain_upper_bound:.3f} "
                        f"displaced_flat={dominance.displaced_flat_value:.3f} "
                        f"required_subtotal_to_match={dominance.required_subtotal_to_match:.3f}"
                    )
                    continue
            else:
                for item in willow_unresolved:
                    print(f"  willow_upper_bound_unresolved={item}")

        pending.append(label)
        print(
            f"  pending: {label} kind={branch.kind.value} "
            f"status={compatibility.status.value} flat_ceiling={branch.flat_ceiling!r} "
            f"percent_ceiling={branch.percent_ceiling!r} "
            f"rule={branch.search_state_rule or '<none>'} "
            f"incumbent_structural_ordinary={incumbent_ordinary:.3f} "
            f"survivor_structural_ordinary={survivor_ordinary:.3f}"
        )

    best_incumbent = max(scored, key=lambda row: row.incumbent_score)
    best_survivor = max(scored, key=lambda row: row.survivor_score)
    best_incumbent_name = "ordinary" if best_incumbent.branch is None else best_incumbent.branch.set_name
    best_survivor_name = "ordinary" if best_survivor.branch is None else best_survivor.branch.set_name
    global_margin = best_survivor.survivor_score - best_incumbent.incumbent_score

    print()
    print("DIRECTLY COMPOSABLE FRONTIER")
    print(
        f"best_incumbent={best_incumbent_name!r} score={best_incumbent.incumbent_score:.3f}"
    )
    print(
        f"best_baron_decisive={best_survivor_name!r} score={best_survivor.survivor_score:.3f}"
    )
    print(f"baron_decisive_margin_vs_best_composable_incumbent={global_margin:.3f}")
    print(f"directly_scored_special_branches={max(0, len(scored) - 1)}")
    print(f"pruned_special_branches={len(pruned)}")
    print(f"pending_special_branches={len(pending)}")
    print("baron_action_proof_pending=True")
    print("decisive_stochastic_proof_pending=True")
    print("ultimate_source_numeric_legality_proven=False")

    if pending:
        print(
            "NEXT_STEP=resolve the remaining search-state special branch before "
            "closing Baron action volume and Decisive stochastic/numeric Ultimate proof"
        )
        return 2
    print(
        "NEXT_STEP=close Baron action volume and Decisive stochastic/numeric Ultimate proof "
        "for the surviving Health Recovery route"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
