from __future__ import annotations

"""Score only production-ordinary Max Magicka packages above the incumbent gear threshold.

The current legal incumbent uses 12,628 exact flat Max Magicka from ordinary gear:
Crafty Alfiq 5pc + Necropotence 4pc + Grace of the Ancients 3pc.  Production ordinary
classification is delegated to ``ExtremeMaxResourceOrdinaryNamedGearSearchService``;
conditional, percentage, unresolved, and search-state-mutating breakpoints are excluded.

Because every production-ordinary retained effect is an unconditional flat ADD to Max
Magicka, any ordinary package with flat delta <= 12,628 cannot beat the incumbent under
the same already-maximized non-gear state.  This audit therefore keeps only DP packages
strictly above that threshold, proves physical legality, and canonically scores every
retained legal witness across the proven armor frontier and both bars.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
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
from services.extreme_armor_resource_trait_glyph_state_service import ExtremeArmorResourceTraitGlyphStateService
from services.extreme_armor_resource_weight_trait_glyph_state_service import ExtremeArmorResourceWeightTraitGlyphStateService
from services.extreme_best_named_gear_resource_armor_mundus_food_potion_structural_stat_evaluator import ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_hypothetical_racial_progression_service import ExtremeHypotheticalRacialProgressionService
from services.extreme_hypothetical_undaunted_progression_service import ExtremeHypotheticalUndauntedProgressionService
from services.extreme_jewelry_resource_static_trait_state_service import ExtremeJewelryResourceStaticTraitStateService
from services.extreme_max_resource_armor_scoring_frontier_service import ExtremeMaxResourceArmorScoringFrontierService
from services.extreme_max_resource_ordinary_named_gear_search_service import ExtremeMaxResourceOrdinaryNamedGearSearchService
from services.extreme_named_gear_set_realization_service import ExtremeNamedGearSetRealization, ExtremeNamedGearSetRealizationService
from services.extreme_named_gear_set_slot_eligibility_service import ExtremeNamedGearSetSlotEligibilityService
from services.extreme_optimization_service import ExtremeOptimizationService
from services.extreme_resource_attribute_projection_service import ExtremeResourceAttributeProjectionService
from services.extreme_resource_class_route_dominance_projection_service import ExtremeResourceClassRouteDominanceProjectionService
from services.extreme_resource_race_projection_service import ExtremeResourceRaceProjectionService
from services.extreme_resource_racial_boundary_relevance_service import ExtremeResourceRacialBoundaryRelevanceService
from services.extreme_structural_core_stat_record_service import ExtremeCanonicalStructuralStatEvaluator
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate
from services.extreme_weapon_resource_relevance_service import ExtremeWeaponResourceRelevanceService

OBJECTIVE = "max_magicka"
ACTIVE_UNITS = 12
INCUMBENT = 107574.0
INCUMBENT_GEAR_DELTA = 12628.0

_ARMOR_BASE_WARNING = re.compile(r"^(Head|Shoulders|Chest|Hands|Waist|Legs|Feet) armor base: CP160 Gold required")
_WEAPON_BASE_WARNING = re.compile(r"^(Front Bar|Back Bar) weapon base: CP160 Gold required")
_RACIAL_BOUNDARY_PREFIXES = (
    "Non-combat racial passive outside combat capability audit:",
    "Racial passive restores current resources or alters mitigation without changing maximum resources:",
    "Racial passive changes consumable duration or skill-line experience without changing maximum resources:",
)


@dataclass(frozen=True)
class Choice:
    set_id: int
    set_name: str
    count: int
    flat_delta: float


@dataclass(frozen=True)
class State:
    units: int
    flat_delta: float
    choices: tuple[Choice, ...]

    @property
    def identity(self) -> tuple[tuple[int, int], ...]:
        return tuple((row.set_id, row.count) for row in self.choices)


@dataclass(frozen=True)
class LegalCandidate:
    state: State
    realization: ExtremeNamedGearSetRealization


def _armor_resolved(build_payload: dict, slot: str) -> bool:
    row = dict((build_payload.get("Armor") or {}).get(slot) or {})
    return (
        str(row.get("Level") or "").strip().casefold() == "cp160"
        and str(row.get("Quality") or "").strip().casefold() == "gold"
    )


def _reconcile(database: Path, unresolved, *, build_payload: dict, weapon_irrelevance: bool):
    effective: list[str] = []
    neutralized: list[str] = []
    racial: list[str] = []
    for raw in unresolved:
        msg = str(raw or "").strip()
        if not msg:
            continue
        armor = _ARMOR_BASE_WARNING.match(msg)
        if armor and _armor_resolved(build_payload, armor.group(1)):
            neutralized.append(msg)
            continue
        if _WEAPON_BASE_WARNING.match(msg) and weapon_irrelevance:
            neutralized.append(msg)
            continue
        if msg.startswith(_RACIAL_BOUNDARY_PREFIXES):
            racial.append(msg)
            continue
        effective.append(msg)
    if racial:
        report = ExtremeResourceRacialBoundaryRelevanceService(database).build(OBJECTIVE, tuple(racial))
        neutralized.extend(report.proven_irrelevant)
        effective.extend(report.unresolved)
    return tuple(dict.fromkeys(effective)), tuple(dict.fromkeys(neutralized))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--incumbent", type=float, default=INCUMBENT)
    parser.add_argument("--gear-threshold", type=float, default=INCUMBENT_GEAR_DELTA)
    parser.add_argument("--frontier-per-units", type=int, default=512)
    args = parser.parse_args()

    database = Path(args.database)
    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)

    ordinary_by_set: dict[int, list[Choice]] = {}
    special_pairs: list[tuple[int, str, int]] = []
    for row in relevance.evidence:
        delta = ExtremeMaxResourceOrdinaryNamedGearSearchService._ordinary_exact_delta(row, OBJECTIVE)
        if delta is None:
            if row.status.value != "proven_irrelevant":
                special_pairs.append((int(row.set_id), str(row.set_name), int(row.piece_count)))
            continue
        if delta <= 0:
            continue
        ordinary_by_set.setdefault(int(row.set_id), []).append(
            Choice(int(row.set_id), str(row.set_name), int(row.piece_count), float(delta))
        )

    for rows in ordinary_by_set.values():
        rows.sort(key=lambda c: (c.count, -c.flat_delta, c.set_name.casefold(), c.set_id))

    keep = max(1, int(args.frontier_per_units))
    frontier: dict[int, tuple[State, ...]] = {0: (State(0, 0.0, ()),)}
    for set_id in sorted(ordinary_by_set):
        buckets: dict[int, dict[tuple[tuple[int, int], ...], State]] = {
            units: {state.identity: state for state in states}
            for units, states in frontier.items()
        }
        for used, states in frontier.items():
            for state in states:
                for choice in ordinary_by_set[set_id]:
                    units = used + choice.count
                    if units > ACTIVE_UNITS:
                        continue
                    candidate = State(units, state.flat_delta + choice.flat_delta, (*state.choices, choice))
                    bucket = buckets.setdefault(units, {})
                    current = bucket.get(candidate.identity)
                    if current is None or candidate.flat_delta > current.flat_delta + 1e-9:
                        bucket[candidate.identity] = candidate
        frontier = {
            units: tuple(sorted(rows.values(), key=lambda s: (-s.flat_delta, -s.units, s.identity))[:keep])
            for units, rows in buckets.items()
        }

    above_threshold = tuple(sorted(
        (
            state
            for states in frontier.values()
            for state in states
            if state.flat_delta > args.gear_threshold + 1e-9
        ),
        key=lambda s: (-s.flat_delta, -s.units, s.identity),
    ))

    topology_catalog = ExtremeGearSetTopologyCatalogService(repository).build()
    topology_by_counts = {tuple(int(v) for v in row.counts): row for row in topology_catalog.topologies}
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    eligibility_by_id = {int(row.set_id): row for row in eligibility.sets}

    legal: list[LegalCandidate] = []
    topology_rejected = physical_rejected = 0
    seen = set()
    for state in above_threshold:
        choices = tuple(sorted(state.choices, key=lambda c: (-c.count, c.set_name.casefold(), c.set_id)))
        topology = topology_by_counts.get(tuple(c.count for c in choices))
        if topology is None:
            topology_rejected += 1
            continue
        named = tuple(eligibility_by_id.get(c.set_id) for c in choices)
        if any(row is None for row in named):
            physical_rejected += 1
            continue
        realization = ExtremeNamedGearSetRealizationService.find_witness(topology, tuple(row for row in named if row is not None))
        if realization is None:
            physical_rejected += 1
            continue
        key = (
            state.identity,
            tuple((row.slot, row.set_id, row.weapon_type) for row in realization.assignments),
        )
        if key in seen:
            continue
        seen.add(key)
        legal.append(LegalCandidate(state, realization))

    legal.sort(key=lambda row: (-row.state.flat_delta, -row.state.units, row.state.identity))

    print("EXTREME MAX MAGICKA CORRECTED ORDINARY THRESHOLD")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print("ordinary_classifier=production _ordinary_exact_delta")
    print(f"incumbent={args.incumbent:.3f}")
    print(f"incumbent_gear_threshold={args.gear_threshold:.3f}")
    print(f"ordinary_named_sets={len(ordinary_by_set)}")
    print(f"special_or_nonordinary_pairs={len(set(special_pairs))}")
    print(f"frontier_per_units={keep}")
    print(f"abstract_above_threshold={len(above_threshold)}")
    print(f"topology_rejected={topology_rejected}")
    print(f"physically_rejected={physical_rejected}")
    print(f"legal_above_threshold={len(legal)}")

    if not legal:
        print("ordinary_above_threshold_closed=True")
        print("NEXT_STEP=ordinary named gear is closed; score special/runtime survivors")
        return 0

    universe = ExtremeGlobalSearchUniverseService(database).build()
    race_projection = ExtremeResourceRaceProjectionService(database).build(OBJECTIVE, tuple(universe.races))
    route_projection = ExtremeResourceClassRouteDominanceProjectionService(database).build(OBJECTIVE, tuple(universe.class_routes))
    attribute_projection = ExtremeResourceAttributeProjectionService.build(OBJECTIVE, tuple(universe.attribute_allocations))
    if not (race_projection.projection_complete and route_projection.projection_complete and attribute_projection.projection_complete):
        raise RuntimeError("Structural Max Magicka witnesses are not proof-complete")

    canonical_race = ExtremeHypotheticalRacialProgressionService._canonical_skill_line_race(race_projection.races[0])
    route = route_projection.routes[0]
    attributes = attribute_projection.allocations[0]
    optimizer = ExtremeOptimizationService(database_path=database)
    canonical = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=optimizer,
        progression_service=ExtremeHypotheticalUndauntedProgressionService(database),
    )
    jewelry_catalog = ExtremeJewelryResourceStaticTraitStateService(database).build(OBJECTIVE)
    jewelry_state = jewelry_catalog.states[0] if jewelry_catalog.states else None
    factory = ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory(
        canonical_evaluator=canonical,
        mundus_repository=MundusRepository(database, game_update=U50_GAME_UPDATE, initialize=False),
        provisioning_repository=ProvisioningStaticRepository(database),
        potion_repository=PotionAvailabilityRepository(database, game_update=GameUpdate.U50),
        jewelry_state=jewelry_state,
    )
    armor_catalog = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
        OBJECTIVE,
        trait_glyph_service=ExtremeArmorResourceTraitGlyphStateService(database),
    ).build(OBJECTIVE)
    armor_frontier = ExtremeMaxResourceArmorScoringFrontierService.build(OBJECTIVE, armor_catalog)
    armor_states = tuple(armor_frontier.states) if armor_frontier.reduction_proven else tuple(armor_catalog.states)
    weapon = ExtremeWeaponResourceRelevanceService(database).build(OBJECTIVE)

    started = perf_counter()
    scored = []
    for rank, candidate in enumerate(legal, start=1):
        for bar in ("front", "back"):
            structural = ExtremeStructuralCandidate(
                race=canonical_race,
                class_route=route,
                attributes=attributes,
                active_bar=bar,
            )
            for armor in armor_states:
                value, payload, raw = factory(candidate.realization, armor)(OBJECTIVE, structural)
                effective, neutralized = _reconcile(
                    database,
                    tuple(raw),
                    build_payload=dict(payload.get("build") or {}),
                    weapon_irrelevance=weapon.objective_irrelevance_proven,
                )
                scored.append((float(value), rank, candidate, bar, armor, dict(payload), tuple(raw), effective, neutralized))

    scored.sort(key=lambda r: (-r[0], len(r[7]), r[1], r[3], r[4].identity))
    best = scored[0]
    elapsed = perf_counter() - started

    print(f"armor_states_scored_per_bar={len(armor_states)}")
    print("active_bars_scored=2")
    print(f"canonical_scores={len(scored)}")
    print(f"elapsed_seconds={elapsed:.3f}")
    print()
    print("TOP CORRECTED ORDINARY SCORES")
    for row in scored[:10]:
        value, rank, candidate, bar, armor, payload, raw, effective, _neutralized = row
        print(
            f"  value={value:.3f} margin_vs_incumbent={value-args.incumbent:.3f} "
            f"source_rank={rank} flat_delta={candidate.state.flat_delta:.3f} "
            f"bar={bar} divines={armor.divines_count} infused={armor.infused_count} "
            f"effective_unresolved={len(effective)}"
        )
        print("    sets=" + ", ".join(
            f"{name} {count}pc"
            for name, count in zip(candidate.realization.set_names, candidate.realization.counts)
        ))

    value, rank, candidate, bar, armor, payload, raw, effective, neutralized = best
    print()
    print("BEST CORRECTED ORDINARY CANDIDATE")
    print(f"value={value:.3f}")
    print(f"incumbent={args.incumbent:.3f}")
    print(f"margin_vs_incumbent={value-args.incumbent:.3f}")
    print(f"beats_incumbent={value > args.incumbent + 1e-9}")
    print(f"source_rank={rank}")
    print(f"flat_delta={candidate.state.flat_delta:.3f}")
    print("sets=" + ", ".join(
        f"{name} {count}pc"
        for name, count in zip(candidate.realization.set_names, candidate.realization.counts)
    ))
    print(f"effective_unresolved={len(effective)}")
    print(f"proof_neutralized_unresolved={len(neutralized)}")
    for item in effective:
        print(f"  unresolved: {item}")
    clean_winner = value > args.incumbent + 1e-9 and not effective
    print(f"ordinary_above_threshold_closed={not clean_winner}")
    print(
        "NEXT_STEP="
        + (
            "promote corrected ordinary winner and rerun threshold proof"
            if clean_winner
            else "ordinary named gear is closed against 107574; score special/runtime survivors"
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
