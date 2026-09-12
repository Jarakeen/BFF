from __future__ import annotations

"""Diagnose exact branch-and-bound pressure for Extreme max-resource named gear.

This starts from the proof-safe equivalence reduction plus the exact-flat objective
frontier.  Mechanic-complete ordinary max-resource breakpoints have an exact flat
``reviewed_delta`` and therefore admit a simple additive upper bound.  Conditional,
unresolved, or search-state-mutating candidates are deliberately treated as
unbounded: any branch that could still select one is kept open rather than being
pruned by an unsafe numeric ceiling.

At complete ordinary leaves we ask the canonical named-slot witness solver whether
the assignment is physically realizable.  This file is diagnostic only; it does not
change production search semantics.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.effects import EffectOperation
from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationService,
)
from tools.audit_extreme_named_gear_objective_frontier import _frontier_reduced_breakpoints


_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


@dataclass(frozen=True)
class _Candidate:
    set_id: int
    name: str
    count: int
    exact_delta: float | None


@dataclass
class _Stats:
    nodes: int = 0
    leaves: int = 0
    feasible_leaves: int = 0
    rejected_leaves: int = 0
    pruned_by_bound: int = 0
    forced_open_nodes: int = 0
    special_leaves: int = 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure branch-and-bound search pressure for Extreme named gear."
    )
    parser.add_argument("--database", default="data/eso.db")
    parser.add_argument("--objective", choices=_OBJECTIVES, default="max_health")
    parser.add_argument(
        "--top",
        type=int,
        default=12,
        help="Number of heaviest topologies to execute. Defaults to 12 for a quick diagnostic.",
    )
    return parser


def _exact_delta(reducer, evidence) -> float | None:
    if evidence.status is not ExtremeGearSetObjectiveRelevance.RELEVANT:
        return None
    if evidence.search_state_rule is not None or evidence.candidate.unresolved:
        return None
    target_stats = ExtremeGearSetObjectiveService._target_stats(reducer.relevance.objective_key)
    target_effects = tuple(
        effect for effect in evidence.candidate.source_effects if effect.stat in target_stats
    )
    if not target_effects:
        return None
    if any(effect.operation is not EffectOperation.ADD for effect in target_effects):
        return None
    if any(effect.condition for effect in target_effects):
        return None
    return float(evidence.reviewed_delta)


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    objective = str(args.objective)

    repository = GearSetRepository(database)
    topology_catalog = ExtremeGearSetTopologyCatalogService(repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(objective, breakpoints)
    reducer = ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )
    equivalent, _equivalent_pruned, representative_limit = reducer.proof_reduced_breakpoints(
        topology_catalog
    )
    frontier, frontier_pruned, frontier_eligible, _frontier_groups = _frontier_reduced_breakpoints(
        reducer=reducer,
        reduced=equivalent,
        representative_limit=representative_limit,
    )

    evidence_by_key = {
        (int(row.set_id), int(row.piece_count)): row for row in relevance.evidence
    }
    eligibility_by_id = {int(row.set_id): row for row in eligibility.sets}

    candidates_by_count: dict[int, tuple[_Candidate, ...]] = {}
    for row in frontier.sets:
        physical = eligibility_by_id.get(int(row.set_id))
        if physical is None or not physical.has_physical_slot_evidence:
            continue
        for count in row.bonus_counts:
            evidence = evidence_by_key.get((int(row.set_id), int(count)))
            if evidence is None:
                continue
            candidate = _Candidate(
                set_id=int(row.set_id),
                name=str(row.name),
                count=int(count),
                exact_delta=_exact_delta(reducer, evidence),
            )
            candidates_by_count.setdefault(int(count), []).append(candidate)

    candidates_by_count = {
        count: tuple(
            sorted(
                rows,
                key=lambda item: (
                    item.exact_delta is None,
                    -(item.exact_delta or 0.0),
                    item.set_id,
                    item.name.casefold(),
                ),
            )
        )
        for count, rows in candidates_by_count.items()
    }

    special_pairs = sum(
        1 for rows in candidates_by_count.values() for row in rows if row.exact_delta is None
    )
    exact_pairs = sum(
        1 for rows in candidates_by_count.values() for row in rows if row.exact_delta is not None
    )

    # Use the same simple combinatorial pressure ordering as the prior diagnostics.
    def pressure(topology) -> int:
        total = 1
        seen: dict[int, int] = {}
        for count in topology.counts:
            seen[count] = seen.get(count, 0) + 1
        from math import comb
        for count, needed in seen.items():
            available = len(candidates_by_count.get(int(count), ()))
            if available < needed:
                return 0
            total *= comb(available, needed)
        return int(total)

    ordered_topologies = tuple(
        sorted(topology_catalog.topologies, key=lambda row: (pressure(row), row.signature), reverse=True)
    )
    limit = max(1, int(args.top))
    selected_topologies = ordered_topologies[:limit]

    print("EXTREME NAMED GEAR BRANCH-AND-BOUND DIAGNOSTIC")
    print(f"Database: {database}")
    print(f"Objective: {objective}")
    print(f"frontier_breakpoints_pruned={frontier_pruned}")
    print(f"frontier_eligible_breakpoints={frontier_eligible}")
    print(f"exact_flat_candidate_pairs={exact_pairs}")
    print(f"conditional_or_special_candidate_pairs={special_pairs}")
    print(f"topologies_executed={len(selected_topologies)}")

    grand = _Stats()

    for topology in selected_topologies:
        counts = tuple(int(value) for value in topology.counts)
        candidate_rows = tuple(candidates_by_count.get(count, ()) for count in counts)
        realizer = ExtremeNamedGearSetCatalogRealizationService(
            breakpoints=frontier,
            eligibility=eligibility,
        )
        stats = _Stats()
        best_exact = float("-inf")
        selected: list[_Candidate] = []
        used_ids: set[int] = set()

        # Admissible suffix bounds. None means an unresolved/special candidate is
        # still available somewhere in the suffix, so numeric pruning is forbidden.
        suffix_best: list[float | None] = [0.0] * (len(counts) + 1)
        running: float | None = 0.0
        for position in range(len(counts) - 1, -1, -1):
            rows = candidate_rows[position]
            if any(row.exact_delta is None for row in rows):
                running = None
            elif running is not None:
                running += max((row.exact_delta or 0.0) for row in rows)
            suffix_best[position] = running

        def visit(position: int, exact_score: float, has_special: bool) -> None:
            nonlocal best_exact
            stats.nodes += 1
            bound = suffix_best[position]
            if not has_special and bound is not None and best_exact != float("-inf"):
                if exact_score + float(bound) < best_exact - 1e-9:
                    stats.pruned_by_bound += 1
                    return
            elif bound is None or has_special:
                stats.forced_open_nodes += 1

            if position >= len(counts):
                stats.leaves += 1
                if has_special:
                    stats.special_leaves += 1
                physical_rows = tuple(eligibility_by_id[item.set_id] for item in selected)
                witness = realizer._find_witness_cached(topology, physical_rows)
                if witness is None:
                    stats.rejected_leaves += 1
                    return
                stats.feasible_leaves += 1
                if not has_special and exact_score > best_exact:
                    best_exact = exact_score
                return

            count = counts[position]
            previous_equal_id: int | None = None
            if position > 0 and counts[position - 1] == count:
                previous_equal_id = int(selected[position - 1].set_id)

            # Special candidates first so the diagnostic exposes their pressure and
            # so ordinary high-score branches establish a useful incumbent quickly.
            rows = candidate_rows[position]
            for row in rows:
                if row.set_id in used_ids:
                    continue
                if previous_equal_id is not None and row.set_id <= previous_equal_id:
                    continue
                selected.append(row)
                used_ids.add(row.set_id)
                visit(
                    position + 1,
                    exact_score + (0.0 if row.exact_delta is None else row.exact_delta),
                    has_special or row.exact_delta is None,
                )
                used_ids.remove(row.set_id)
                selected.pop()

        visit(0, 0.0, False)

        for field in vars(grand):
            setattr(grand, field, getattr(grand, field) + getattr(stats, field))

        best_text = "none" if best_exact == float("-inf") else f"{best_exact:.3f}"
        print(
            f"{topology.signature}: pressure={pressure(topology)} nodes={stats.nodes} "
            f"leaves={stats.leaves} feasible={stats.feasible_leaves} rejected={stats.rejected_leaves} "
            f"pruned={stats.pruned_by_bound} forced_open={stats.forced_open_nodes} "
            f"special_leaves={stats.special_leaves} best_exact_flat_delta={best_text}"
        )

    print("TOTAL")
    print(f"nodes={grand.nodes}")
    print(f"leaves={grand.leaves}")
    print(f"feasible_leaves={grand.feasible_leaves}")
    print(f"rejected_leaves={grand.rejected_leaves}")
    print(f"pruned_by_bound={grand.pruned_by_bound}")
    print(f"forced_open_nodes={grand.forced_open_nodes}")
    print(f"special_leaves={grand.special_leaves}")

    unresolved = tuple(dict.fromkeys((*frontier.unresolved, *relevance.unresolved)))
    if unresolved:
        print("UNRESOLVED")
        for item in unresolved:
            print(f"  {item}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
