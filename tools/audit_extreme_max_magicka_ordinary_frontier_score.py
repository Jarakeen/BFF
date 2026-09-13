from __future__ import annotations

"""Materialize and canonically score the strongest ordinary Max Magicka DP frontier.

This audit starts from the same complete ordinary breakpoint denominator used by
``audit_extreme_max_magicka_incumbent_pruning.py``. Instead of retaining only the
single best abstract knapsack witness per set-count total, it keeps the top K exact
flat-Max-Magicka packages per total. Those abstract packages are then filtered
through canonical physical slot legality and only the strongest legal witnesses are
canonically scored across the proven Max Magicka armor frontier and both bars.

Special/unresolved/search-state-mutating sets remain outside this ordinary proof
bucket and are reported separately by the incumbent-pruning audit.
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
from minmax.effects import EffectOperation
from minmax.gear_set_repository import GearSetRepository
from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from minmax.potion_availability_repository import PotionAvailabilityRepository
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from minmax.stat_ids import StatId
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
from services.extreme_hypothetical_racial_progression_service import (
    ExtremeHypotheticalRacialProgressionService,
)
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
from services.extreme_resource_racial_boundary_relevance_service import (
    ExtremeResourceRacialBoundaryRelevanceService,
)
from services.extreme_structural_core_stat_record_service import (
    ExtremeCanonicalStructuralStatEvaluator,
)
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate
from services.extreme_weapon_resource_relevance_service import (
    ExtremeWeaponResourceRelevanceService,
)

OBJECTIVE = "max_magicka"
TARGET = StatId.MAX_MAGICKA
ACTIVE_UNITS = 12
INCUMBENT = 107574.0

_ARMOR_BASE_WARNING = re.compile(
    r"^(Head|Shoulders|Chest|Hands|Waist|Legs|Feet) armor base: CP160 Gold required"
)
_WEAPON_BASE_WARNING = re.compile(
    r"^(Front Bar|Back Bar) weapon base: CP160 Gold required"
)
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
        return tuple((choice.set_id, choice.count) for choice in self.choices)


@dataclass(frozen=True)
class LegalCandidate:
    state: State
    realization: ExtremeNamedGearSetRealization

    @property
    def identity(self) -> tuple[object, ...]:
        return (
            self.state.identity,
            tuple(
                (row.slot, row.set_id, row.weapon_type)
                for row in self.realization.assignments
            ),
        )


def _flat_delta(row) -> float:
    return float(
        sum(
            float(effect.value)
            for effect in row.candidate.source_effects
            if effect.stat is TARGET and effect.operation is EffectOperation.ADD
        )
    )


def _state_sort_key(state: State) -> tuple[object, ...]:
    return (
        -float(state.flat_delta),
        -int(state.units),
        state.identity,
    )


def _armor_metadata_proves_resolved(build_payload: dict, slot_name: str) -> bool:
    armor = dict(build_payload.get("Armor") or {})
    row = dict(armor.get(slot_name) or {})
    level = str(row.get("Level") or "").strip().casefold()
    quality = str(row.get("Quality") or "").strip().casefold()
    return level == "cp160" and quality == "gold"


def _reconcile_unresolved(
    database: Path,
    unresolved: tuple[str, ...],
    *,
    build_payload: dict,
    weapon_irrelevance_proven: bool,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    effective: list[str] = []
    neutralized: list[str] = []
    racial: list[str] = []

    for raw in unresolved:
        message = str(raw or "").strip()
        if not message:
            continue

        armor_match = _ARMOR_BASE_WARNING.match(message)
        if armor_match and _armor_metadata_proves_resolved(
            build_payload,
            armor_match.group(1),
        ):
            neutralized.append(message)
            continue

        if _WEAPON_BASE_WARNING.match(message) and weapon_irrelevance_proven:
            neutralized.append(message)
            continue

        if message.startswith(_RACIAL_BOUNDARY_PREFIXES):
            racial.append(message)
            continue

        effective.append(message)

    if racial:
        result = ExtremeResourceRacialBoundaryRelevanceService(database).build(
            OBJECTIVE,
            tuple(racial),
        )
        neutralized.extend(result.proven_irrelevant)
        effective.extend(result.unresolved)

    return (
        tuple(dict.fromkeys(str(item) for item in effective if str(item))),
        tuple(dict.fromkeys(str(item) for item in neutralized if str(item))),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--incumbent", type=float, default=INCUMBENT)
    parser.add_argument("--frontier-per-units", type=int, default=80)
    parser.add_argument("--abstract-limit", type=int, default=400)
    parser.add_argument("--legal-limit", type=int, default=40)
    args = parser.parse_args()

    database = Path(args.database)
    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(
        OBJECTIVE,
        breakpoints,
    )

    ordinary_by_set: dict[int, list[Choice]] = {}
    special_rows = []
    for row in relevance.evidence:
        if row.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
            continue
        if row.search_state_rule is not None or row.candidate.unresolved:
            special_rows.append(row)
            continue
        target_effects = tuple(
            effect for effect in row.candidate.source_effects if effect.stat is TARGET
        )
        invalid = tuple(
            effect for effect in target_effects
            if effect.operation is not EffectOperation.ADD
        )
        if invalid:
            raise RuntimeError(
                "Mechanic-complete ordinary Max Magicka row has non-flat effect: "
                f"{row.set_name} {row.piece_count}pc"
            )
        delta = _flat_delta(row)
        if delta <= 0.0:
            continue
        ordinary_by_set.setdefault(int(row.set_id), []).append(
            Choice(
                set_id=int(row.set_id),
                set_name=row.set_name,
                count=int(row.piece_count),
                flat_delta=delta,
            )
        )

    for rows in ordinary_by_set.values():
        rows.sort(
            key=lambda choice: (
                int(choice.count),
                -float(choice.flat_delta),
                choice.set_name.casefold(),
                int(choice.set_id),
            )
        )

    keep_per_units = max(1, int(args.frontier_per_units))
    frontier: dict[int, tuple[State, ...]] = {0: (State(0, 0.0, ()),)}

    # Top-K multiple-choice knapsack. Because named sets are processed exactly once,
    # retaining the top K histories per used-unit count is sufficient for the top K
    # continuations at every later stage.
    for set_id in sorted(ordinary_by_set):
        next_rows: dict[int, dict[tuple[tuple[int, int], ...], State]] = {
            units: {state.identity: state for state in states}
            for units, states in frontier.items()
        }
        for used, states in frontier.items():
            for state in states:
                for choice in ordinary_by_set[set_id]:
                    total_units = int(used) + int(choice.count)
                    if total_units > ACTIVE_UNITS:
                        continue
                    candidate = State(
                        units=total_units,
                        flat_delta=float(state.flat_delta) + float(choice.flat_delta),
                        choices=(*state.choices, choice),
                    )
                    bucket = next_rows.setdefault(total_units, {})
                    incumbent = bucket.get(candidate.identity)
                    if (
                        incumbent is None
                        or candidate.flat_delta > incumbent.flat_delta + 1e-9
                    ):
                        bucket[candidate.identity] = candidate

        frontier = {}
        for units, by_identity in next_rows.items():
            ordered = tuple(sorted(by_identity.values(), key=_state_sort_key))
            frontier[int(units)] = ordered[:keep_per_units]

    abstract = tuple(
        sorted(
            (
                state
                for units, states in frontier.items()
                if int(units) > 0
                for state in states
            ),
            key=_state_sort_key,
        )
    )[: max(1, int(args.abstract_limit))]

    topology_catalog = ExtremeGearSetTopologyCatalogService(repository).build()
    topology_by_counts = {
        tuple(int(value) for value in row.counts): row
        for row in topology_catalog.topologies
    }
    eligibility_catalog = ExtremeNamedGearSetSlotEligibilityService(database).build()
    eligibility_by_id = {int(row.set_id): row for row in eligibility_catalog.sets}

    legal: dict[tuple[object, ...], LegalCandidate] = {}
    physically_rejected = 0
    topology_rejected = 0
    for state in abstract:
        ordered_choices = tuple(
            sorted(
                state.choices,
                key=lambda choice: (
                    -int(choice.count),
                    choice.set_name.casefold(),
                    choice.set_name,
                    int(choice.set_id),
                ),
            )
        )
        counts = tuple(int(choice.count) for choice in ordered_choices)
        topology = topology_by_counts.get(counts)
        if topology is None:
            topology_rejected += 1
            continue
        named_sets = tuple(
            eligibility_by_id.get(int(choice.set_id))
            for choice in ordered_choices
        )
        if any(row is None for row in named_sets):
            physically_rejected += 1
            continue
        realization = ExtremeNamedGearSetRealizationService.find_witness(
            topology,
            tuple(row for row in named_sets if row is not None),
        )
        if realization is None:
            physically_rejected += 1
            continue
        candidate = LegalCandidate(state=state, realization=realization)
        legal.setdefault(candidate.identity, candidate)

    ranked_legal = tuple(
        sorted(
            legal.values(),
            key=lambda item: (
                -float(item.state.flat_delta),
                -int(item.state.units),
                item.identity,
            ),
        )
    )
    retained_legal = ranked_legal[: max(1, int(args.legal_limit))]
    if not retained_legal:
        raise RuntimeError("Ordinary Max Magicka DP frontier produced no legal physical witness")

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
        raise RuntimeError("Structural Max Magicka witnesses are not proof-complete")

    search_race = race_projection.races[0]
    canonical_race = ExtremeHypotheticalRacialProgressionService._canonical_skill_line_race(
        search_race
    )
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
        tuple(armor_frontier.states)
        if armor_frontier.reduction_proven
        else tuple(armor_catalog.states)
    )
    if not armor_states:
        raise RuntimeError("No Max Magicka armor states available")

    weapon_audit = ExtremeWeaponResourceRelevanceService(database).build(OBJECTIVE)

    scored = []
    started = perf_counter()
    for source_rank, gear_candidate in enumerate(retained_legal, start=1):
        for active_bar in ("front", "back"):
            structural = ExtremeStructuralCandidate(
                race=canonical_race,
                class_route=route,
                attributes=attributes,
                active_bar=active_bar,
            )
            for armor_state in armor_states:
                evaluator = factory(gear_candidate.realization, armor_state)
                value, payload, raw_unresolved = evaluator(OBJECTIVE, structural)
                effective, neutralized = _reconcile_unresolved(
                    database,
                    tuple(str(item) for item in raw_unresolved if str(item)),
                    build_payload=dict(payload.get("build") or {}),
                    weapon_irrelevance_proven=weapon_audit.objective_irrelevance_proven,
                )
                scored.append(
                    (
                        float(value),
                        source_rank,
                        gear_candidate,
                        active_bar,
                        armor_state,
                        dict(payload),
                        tuple(raw_unresolved),
                        effective,
                        neutralized,
                    )
                )

    elapsed = perf_counter() - started
    scored.sort(
        key=lambda row: (
            -float(row[0]),
            len(row[7]),
            int(row[1]),
            row[3],
            row[4].identity,
            row[2].identity,
        )
    )
    best = scored[0]

    print("EXTREME MAX MAGICKA ORDINARY DP FRONTIER SCORE")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print(f"incumbent={args.incumbent:.3f}")
    print(f"ordinary_named_sets={len(ordinary_by_set)}")
    print(f"ordinary_breakpoints={sum(len(rows) for rows in ordinary_by_set.values())}")
    print(f"frontier_per_units={keep_per_units}")
    print(f"abstract_packages_retained={len(abstract)}")
    print(f"topology_rejected={topology_rejected}")
    print(f"physically_rejected={physically_rejected}")
    print(f"legal_frontier_candidates={len(ranked_legal)}")
    print(f"legal_candidates_scored={len(retained_legal)}")
    print(f"armor_states_scored_per_bar={len(armor_states)}")
    print("active_bars_scored=2")
    print(f"canonical_scores={len(scored)}")
    print(f"elapsed_seconds={elapsed:.3f}")
    print()

    print("TOP LEGAL ABSTRACT PACKAGES")
    for candidate in ranked_legal[:10]:
        print(
            f"  flat_delta={candidate.state.flat_delta:.3f} units={candidate.state.units} "
            + "package="
            + ", ".join(
                f"{choice.set_name} {choice.count}pc"
                for choice in candidate.state.choices
            )
        )
    print()

    print("TOP CANONICAL ORDINARY SCORES")
    for row in scored[:10]:
        value, source_rank, candidate, bar, armor, payload, raw, effective, neutralized = row
        print(
            f"  value={value:.3f} margin_vs_incumbent={value - args.incumbent:.3f} "
            f"source_rank={source_rank} flat_delta={candidate.state.flat_delta:.3f} "
            f"bar={bar} divines={armor.divines_count} infused={armor.infused_count} "
            f"effective_unresolved={len(effective)} raw_unresolved={len(raw)}"
        )
        print(
            "    sets="
            + ", ".join(
                f"{name} {count}pc"
                for name, count in zip(
                    candidate.realization.set_names,
                    candidate.realization.counts,
                )
            )
        )
        for key in ("mundus", "food", "potion", "active_buffs"):
            if key in payload:
                print(f"    {key}={payload[key]!r}")
        if effective:
            for item in effective[:5]:
                print(f"    unresolved: {item}")
        if neutralized:
            print(f"    proof_neutralized={len(neutralized)}")

    value, source_rank, candidate, bar, armor, payload, raw, effective, neutralized = best
    print()
    print("BEST ORDINARY FRONTIER CANDIDATE")
    print(f"value={value:.3f}")
    print(f"incumbent={args.incumbent:.3f}")
    print(f"margin_vs_incumbent={value - args.incumbent:.3f}")
    print(f"beats_incumbent={value > args.incumbent + 1e-9}")
    print(f"source_rank={source_rank}")
    print(f"flat_delta={candidate.state.flat_delta:.3f}")
    print(
        "sets="
        + ", ".join(
            f"{name} {count}pc"
            for name, count in zip(
                candidate.realization.set_names,
                candidate.realization.counts,
            )
        )
    )
    print(f"active_bar={bar}")
    print(
        f"armor=types:{armor.armor_type_count} divines:{armor.divines_count} "
        f"infused:{armor.infused_count}"
    )
    print(f"raw_unresolved={len(raw)}")
    print(f"proof_neutralized_unresolved={len(neutralized)}")
    print(f"effective_unresolved={len(effective)}")
    for item in effective:
        print(f"  unresolved: {item}")
    print("payload_race=" + str(payload.get("race") or ""))
    print()
    print(
        "NEXT_STEP="
        + (
            "promote this clean ordinary winner to the incumbent, then rerun incumbent pruning against the higher threshold"
            if value > args.incumbent + 1e-9 and not effective
            else (
                "ordinary frontier did not beat the incumbent; widen the DP frontier only if proof coverage requires it, then close special survivors"
                if not effective
                else "resolve effective warnings before changing the incumbent"
            )
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
