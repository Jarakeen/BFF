from __future__ import annotations

"""Construct and canonically score a small Max Magicka high-water candidate frontier.

This diagnostic is intentionally not an exhaustive named-gear search. It takes a
shortlist of the strongest reviewed Max Magicka sets, builds legal active-snapshot
piece-count combinations, proves a concrete physical slot witness for each one, then
scores only the highest reviewed-potential packages through the canonical Extreme
pipeline.

The result is a real scored high-water mark that can guide proof work. It is not, by
itself, a global-record proof.
"""

import argparse
from dataclasses import dataclass
from itertools import combinations, product
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.combat_effect_semantics import GameUpdate
from minmax.gear_set_repository import GearSetRepository
from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from minmax.potion_availability_repository import PotionAvailabilityRepository
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from services.extreme_armor_resource_trait_glyph_state_service import (
    ExtremeArmorResourceTraitGlyphStateService,
)
from services.extreme_armor_resource_weight_trait_glyph_state_service import (
    ExtremeArmorResourceWeightTraitGlyphStateService,
)
from services.extreme_best_named_gear_resource_armor_mundus_food_potion_structural_stat_evaluator import (
    ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory,
)
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointService,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetTopologyCatalogService,
)
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_hypothetical_undaunted_progression_service import (
    ExtremeHypotheticalUndauntedProgressionService,
)
from services.extreme_jewelry_resource_static_trait_state_service import (
    ExtremeJewelryResourceStaticTraitStateService,
)
from services.extreme_max_resource_armor_scoring_frontier_service import (
    ExtremeMaxResourceArmorScoringFrontierService,
)
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSetRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_optimization_service import ExtremeOptimizationService
from services.extreme_resource_attribute_projection_service import (
    ExtremeResourceAttributeProjectionService,
)
from services.extreme_resource_class_route_dominance_projection_service import (
    ExtremeResourceClassRouteDominanceProjectionService,
)
from services.extreme_resource_race_projection_service import (
    ExtremeResourceRaceProjectionService,
)
from services.extreme_structural_core_stat_record_service import (
    ExtremeCanonicalStructuralStatEvaluator,
)
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate


OBJECTIVE = "max_magicka"
DEFAULT_SET_SHORTLIST = (
    "Necropotence",
    "Crafty Alfiq",
    "Druid's Braid",
    "Bright-Throat's Boast",
    "Robes of Destruction Mastery",
    "Grace of the Ancients",
    "Hanu's Compassion",
    "Xoryn's Masterpiece",
    "Twice-Born Star",
    "Death Dealer's Fete",
    "Prowler's Talisman",
)


@dataclass(frozen=True)
class _BreakpointChoice:
    set_id: int
    set_name: str
    count: int
    reviewed_delta: float
    special: bool


@dataclass(frozen=True)
class _GearCandidate:
    realization: ExtremeNamedGearSetRealization
    reviewed_delta: float
    special_count: int

    @property
    def identity(self) -> tuple[object, ...]:
        return (
            tuple(self.realization.set_ids),
            tuple(self.realization.counts),
            self.realization.weapon_shape.value,
            tuple(
                (row.slot, row.set_id, row.weapon_type)
                for row in self.realization.assignments
            ),
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--target", type=float, default=100000.0)
    parser.add_argument("--candidate-limit", type=int, default=40)
    parser.add_argument("--max-sets", type=int, default=4)
    parser.add_argument(
        "--set",
        dest="sets",
        action="append",
        help="Override shortlist; repeat for each named set.",
    )
    return parser


def _choice_key(row: _BreakpointChoice) -> tuple[object, ...]:
    return (
        -float(row.reviewed_delta),
        -int(row.count),
        row.set_name.casefold(),
        row.set_name,
        int(row.set_id),
    )


def _candidate_key(row: _GearCandidate) -> tuple[object, ...]:
    return (
        -float(row.reviewed_delta),
        -int(row.special_count),
        row.identity,
    )


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    shortlist = tuple(dict.fromkeys(args.sets or DEFAULT_SET_SHORTLIST))

    gear_repository = GearSetRepository(database)
    topology_catalog = ExtremeGearSetTopologyCatalogService(gear_repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(gear_repository).build()
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(gear_repository).build(
        OBJECTIVE,
        breakpoints,
    )

    eligibility_by_id = {int(row.set_id): row for row in eligibility.sets}
    topology_by_counts = {
        tuple(int(value) for value in row.counts): row
        for row in topology_catalog.topologies
    }

    selected = {name.casefold() for name in shortlist}
    choices_by_set: dict[int, list[_BreakpointChoice]] = {}
    for row in relevance.evidence:
        if row.set_name.casefold() not in selected:
            continue
        if row.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
            continue
        special = bool(row.search_state_rule is not None or row.candidate.unresolved)
        if float(row.reviewed_delta) <= 0.0 and not special:
            continue
        choices_by_set.setdefault(int(row.set_id), []).append(
            _BreakpointChoice(
                set_id=int(row.set_id),
                set_name=row.set_name,
                count=int(row.piece_count),
                reviewed_delta=float(row.reviewed_delta),
                special=special,
            )
        )

    for values in choices_by_set.values():
        values.sort(key=_choice_key)

    set_ids = tuple(
        sorted(
            choices_by_set,
            key=lambda set_id: (
                choices_by_set[set_id][0].set_name.casefold(),
                choices_by_set[set_id][0].set_name,
                set_id,
            ),
        )
    )

    realized: dict[tuple[object, ...], _GearCandidate] = {}
    max_sets = max(1, min(int(args.max_sets), len(set_ids)))
    packages_considered = 0
    packages_capacity_valid = 0
    packages_physically_realized = 0

    for size in range(1, max_sets + 1):
        for ids in combinations(set_ids, size):
            choice_lists = tuple(tuple(choices_by_set[set_id]) for set_id in ids)
            for picked in product(*choice_lists):
                packages_considered += 1
                used = sum(int(row.count) for row in picked)
                if used <= 0 or used > 12:
                    continue

                ordered = tuple(
                    sorted(
                        picked,
                        key=lambda row: (-int(row.count), row.set_name.casefold(), row.set_name),
                    )
                )
                counts = tuple(int(row.count) for row in ordered)
                topology = topology_by_counts.get(counts)
                if topology is None:
                    continue
                packages_capacity_valid += 1

                named_sets = tuple(eligibility_by_id.get(int(row.set_id)) for row in ordered)
                if any(item is None for item in named_sets):
                    continue
                realization = ExtremeNamedGearSetRealizationService.find_witness(
                    topology,
                    tuple(item for item in named_sets if item is not None),
                )
                if realization is None:
                    continue
                packages_physically_realized += 1

                candidate = _GearCandidate(
                    realization=realization,
                    reviewed_delta=sum(float(row.reviewed_delta) for row in ordered),
                    special_count=sum(1 for row in ordered if row.special),
                )
                incumbent = realized.get(candidate.identity)
                if incumbent is None or _candidate_key(candidate) < _candidate_key(incumbent):
                    realized[candidate.identity] = candidate

    ranked = tuple(sorted(realized.values(), key=_candidate_key))
    retained = ranked[: max(1, int(args.candidate_limit))]
    if not retained:
        raise RuntimeError("Constructive Max Magicka audit produced no legal named-gear candidates")

    universe = ExtremeGlobalSearchUniverseService(database).build()
    race_projection = ExtremeResourceRaceProjectionService(database).build(
        OBJECTIVE,
        tuple(universe.races),
    )
    route_projection = ExtremeResourceClassRouteDominanceProjectionService(database).build(
        OBJECTIVE,
        tuple(universe.class_routes),
    )
    attribute_projection = ExtremeResourceAttributeProjectionService.build(
        OBJECTIVE,
        tuple(universe.attribute_allocations),
    )
    if not (
        race_projection.projection_complete
        and route_projection.projection_complete
        and attribute_projection.projection_complete
    ):
        raise RuntimeError("Constructive structural Max Magicka witnesses are not proof-complete")

    optimizer = ExtremeOptimizationService(database_path=database)
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=optimizer,
        progression_service=ExtremeHypotheticalUndauntedProgressionService(database),
    )
    jewelry_catalog = ExtremeJewelryResourceStaticTraitStateService(database).build(OBJECTIVE)
    jewelry_state = jewelry_catalog.states[0] if jewelry_catalog.states else None
    factory = ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory(
        canonical_evaluator=canonical,
        mundus_repository=MundusRepository(
            database,
            game_update=U50_GAME_UPDATE,
            initialize=False,
        ),
        provisioning_repository=ProvisioningStaticRepository(database),
        potion_repository=PotionAvailabilityRepository(
            database,
            game_update=GameUpdate.U50,
        ),
        jewelry_state=jewelry_state,
    )

    armor_catalog = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
        OBJECTIVE,
        trait_glyph_service=ExtremeArmorResourceTraitGlyphStateService(database),
    ).build(OBJECTIVE)
    armor_frontier = ExtremeMaxResourceArmorScoringFrontierService.build(
        OBJECTIVE,
        armor_catalog,
    )
    armor_states = (
        armor_frontier.states
        if armor_frontier.reduction_proven
        else tuple(armor_catalog.states)
    )
    if not armor_states:
        raise RuntimeError("Constructive Max Magicka audit produced no armor states")

    scored = []
    started = perf_counter()
    race = race_projection.races[0]
    route = route_projection.routes[0]
    attributes = attribute_projection.allocations[0]

    for rank, gear_candidate in enumerate(retained, start=1):
        for active_bar in ("front", "back"):
            structural = ExtremeStructuralCandidate(
                race=race,
                class_route=route,
                attributes=attributes,
                active_bar=active_bar,
            )
            for armor_state in armor_states:
                evaluator = factory(gear_candidate.realization, armor_state)
                value, payload, unresolved = evaluator(OBJECTIVE, structural)
                scored.append(
                    (
                        float(value),
                        rank,
                        gear_candidate,
                        active_bar,
                        armor_state,
                        dict(payload),
                        tuple(str(item) for item in unresolved if str(item)),
                    )
                )

    elapsed = perf_counter() - started
    scored.sort(
        key=lambda item: (
            -item[0],
            item[1],
            item[3],
            item[4].identity,
            item[2].identity,
        )
    )

    print("EXTREME MAX MAGICKA CONSTRUCTIVE CANDIDATE SCORE")
    print(f"database={database}")
    print(f"target={args.target:g}")
    print("mode=small_legal_constructive_frontier_canonical_scoring")
    print(f"shortlist_sets={len(shortlist)}")
    print("shortlist=" + ", ".join(shortlist))
    print(f"packages_considered={packages_considered}")
    print(f"packages_capacity_valid={packages_capacity_valid}")
    print(f"packages_physically_realized={packages_physically_realized}")
    print(f"unique_legal_realizations={len(ranked)}")
    print(f"gear_candidates_scored={len(retained)}")
    print(f"armor_states_scored_per_bar={len(armor_states)}")
    print(f"active_bars_scored=2")
    print(f"canonical_scores={len(scored)}")
    print(f"elapsed_seconds={elapsed:.3f}")
    print()

    print("TOP CANONICAL SCORES")
    for item in scored[:10]:
        value, source_rank, gear_candidate, active_bar, armor_state, payload, unresolved = item
        realization = gear_candidate.realization
        sets = ", ".join(
            f"{name} {count}pc"
            for name, count in zip(realization.set_names, realization.counts)
        )
        print(
            f"  value={value:.3f} gap_to_target={args.target - value:.3f} "
            f"gear_rank={source_rank} reviewed_gear_delta={gear_candidate.reviewed_delta:g} "
            f"bar={active_bar} armor_types={armor_state.armor_type_count} "
            f"divines={armor_state.divines_count} infused={armor_state.infused_count}"
        )
        print(f"    sets={sets}")
        print(
            "    slots="
            + ", ".join(
                f"{row.slot}:{row.set_name}{('/' + row.weapon_type) if row.weapon_type else ''}"
                for row in realization.assignments
            )
        )
        for key in ("mundus", "food", "potion", "active_buffs"):
            if key in payload:
                print(f"    {key}={payload[key]!r}")
        print(f"    unresolved={len(unresolved)}")

    best = scored[0]
    best_value, _rank, best_gear, best_bar, best_armor, best_payload, best_unresolved = best
    print()
    print("BEST HIGH-WATER CANDIDATE")
    print(f"value={best_value:.3f}")
    print(f"target={args.target:g}")
    print(f"gap_to_target={args.target - best_value:.3f}")
    print(f"meets_target={best_value >= args.target}")
    print(f"race={race}")
    print(
        f"class_route={route.base_class.value} subclassed={route.is_subclassed} "
        f"lines={tuple(route.equipped_skill_lines)!r}"
    )
    print(f"attributes={attributes!r}")
    print(f"active_bar={best_bar}")
    print(
        "sets="
        + ", ".join(
            f"{name} {count}pc"
            for name, count in zip(best_gear.realization.set_names, best_gear.realization.counts)
        )
    )
    print(
        f"armor=types:{best_armor.armor_type_count} divines:{best_armor.divines_count} "
        f"infused:{best_armor.infused_count} direct_glyph_delta:{best_armor.trait_glyph_state.direct_glyph_delta:g}"
    )
    print(f"unresolved={len(best_unresolved)}")
    for item in best_unresolved[:20]:
        print(f"  unresolved: {item}")
    print("payload_keys=" + ",".join(sorted(best_payload)))
    print()
    print(
        "NOTE: this is a canonically scored constructive high-water frontier, not a global "
        "record proof. If it gets close to or exceeds the target, the next proof step is to "
        "show omitted named-gear packages cannot beat it rather than enumerate them all."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
