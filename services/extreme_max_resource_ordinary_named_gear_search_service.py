from __future__ import annotations

"""Exact branch-and-bound search for ordinary max-resource named gear.

This service owns only the mechanic-complete, ordinary named-set branch for
Max Health, Max Magicka, and Max Stamina.  Search-state mutators, conditional
resource effects, and unresolved candidates remain explicit exclusions and must
be composed by a higher layer before the *full* named-gear denominator can close.

For the ordinary branch, every retained requested-resource effect is an exact
flat ADD contribution.  The search therefore admits an additive optimistic bound.
It also applies the canonical optimistic partial physical-feasibility contract,
which may prune a branch only when the already-selected prefix cannot fit any
canonical active-snapshot physical realization even if all future sets are treated
as unconstrained.
"""

from dataclasses import dataclass

from minmax.effects import EffectOperation
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
    ExtremeGearSetBonusBreakpoints,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveBreakpointEvidence,
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceCatalog,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetCountTopology,
    ExtremeGearSetTopologyCatalog,
)
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationService,
)
from services.extreme_named_gear_set_realization_service import ExtremeNamedGearSetRealization
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
    ExtremeNamedGearSetSlotEligibilityCatalog,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationService,
)
from services.extreme_partial_named_gear_physical_feasibility_service import (
    ExtremePartialNamedGearPhysicalFeasibilityService,
)


@dataclass(frozen=True)
class ExtremeOrdinaryNamedGearSearchStats:
    nodes: int = 0
    leaves: int = 0
    witness_checks: int = 0
    feasible_leaves: int = 0
    rejected_leaves: int = 0
    score_pruned: int = 0
    physical_pruned: int = 0


@dataclass(frozen=True)
class ExtremeOrdinaryNamedGearTopologyWinner:
    topology: ExtremeGearSetCountTopology
    best_exact_flat_delta: float | None
    realizations: tuple[ExtremeNamedGearSetRealization, ...]
    stats: ExtremeOrdinaryNamedGearSearchStats

    @property
    def winner_found(self) -> bool:
        return self.best_exact_flat_delta is not None and bool(self.realizations)


@dataclass(frozen=True)
class ExtremeMaxResourceOrdinaryNamedGearSearchResult:
    objective_key: str
    topologies: tuple[ExtremeOrdinaryNamedGearTopologyWinner, ...]
    equivalent_breakpoints_pruned: int
    frontier_breakpoints_pruned: int
    representative_limit: int
    special_or_nonflat_pairs: tuple[tuple[int, str, int], ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def ordinary_denominator_proven(self) -> bool:
        return not self.unresolved

    @property
    def full_named_gear_denominator_proven(self) -> bool:
        return self.ordinary_denominator_proven and not self.special_or_nonflat_pairs

    @property
    def winning_realizations(self) -> tuple[ExtremeNamedGearSetRealization, ...]:
        rows: list[ExtremeNamedGearSetRealization] = []
        for topology in self.topologies:
            rows.extend(topology.realizations)
        return tuple(rows)


@dataclass(frozen=True)
class _Candidate:
    set_id: int
    name: str
    piece_count: int
    exact_delta: float
    eligibility: ExtremeNamedGearSetSlotEligibility


class ExtremeMaxResourceOrdinaryNamedGearSearchService:
    """Proof-safe exact ordinary named-gear search for max-resource objectives."""

    SUPPORTED_OBJECTIVES = frozenset({"max_health", "max_magicka", "max_stamina"})

    def __init__(
        self,
        *,
        breakpoints: ExtremeGearSetBonusBreakpointCatalog,
        eligibility: ExtremeNamedGearSetSlotEligibilityCatalog,
        relevance: ExtremeGearSetObjectiveRelevanceCatalog,
    ) -> None:
        self.breakpoints = breakpoints
        self.eligibility = eligibility
        self.relevance = relevance

    @staticmethod
    def _ordinary_exact_delta(
        evidence: ExtremeGearSetObjectiveBreakpointEvidence,
        objective_key: str,
    ) -> float | None:
        if evidence.status is not ExtremeGearSetObjectiveRelevance.RELEVANT:
            return None
        if evidence.search_state_rule is not None or evidence.candidate.unresolved:
            return None
        target_stats = ExtremeGearSetObjectiveService._target_stats(objective_key)
        effects = tuple(
            effect
            for effect in evidence.candidate.source_effects
            if effect.stat in target_stats
        )
        if not effects:
            return None
        if any(effect.operation is not EffectOperation.ADD for effect in effects):
            return None
        if any(effect.condition for effect in effects):
            return None
        return float(evidence.reviewed_delta)

    def _frontier(
        self,
        reduced: ExtremeGearSetBonusBreakpointCatalog,
        representative_limit: int,
    ) -> tuple[ExtremeGearSetBonusBreakpointCatalog, int]:
        reducer = ExtremeObjectiveNamedGearSetCatalogRealizationService(
            breakpoints=self.breakpoints,
            eligibility=self.eligibility,
            relevance=self.relevance,
        )
        evidence_by_key = {
            (int(row.set_id), int(row.piece_count)): row
            for row in self.relevance.evidence
        }
        eligibility_by_id = {int(row.set_id): row for row in self.eligibility.sets}

        groups: dict[
            tuple[object, ...],
            list[tuple[int, str, int, float]],
        ] = {}
        for breakpoint_set in reduced.sets:
            physical = eligibility_by_id.get(int(breakpoint_set.set_id))
            if physical is None or not physical.has_physical_slot_evidence:
                continue
            for count in breakpoint_set.bonus_counts:
                evidence = evidence_by_key.get((int(breakpoint_set.set_id), int(count)))
                if evidence is None:
                    continue
                delta = self._ordinary_exact_delta(evidence, self.relevance.objective_key)
                if delta is None:
                    continue
                key = (
                    int(count),
                    reducer._eligibility_signature(physical),
                )
                groups.setdefault(key, []).append(
                    (
                        int(breakpoint_set.set_id),
                        str(breakpoint_set.name),
                        int(count),
                        float(delta),
                    )
                )

        limit = max(1, int(representative_limit))
        pruned_pairs: set[tuple[int, int]] = set()
        for members in groups.values():
            ordered = tuple(
                sorted(
                    members,
                    key=lambda item: (
                        -item[3],
                        item[0],
                        item[1].casefold(),
                        item[1],
                    ),
                )
            )
            for set_id, _name, count, _delta in ordered[limit:]:
                pruned_pairs.add((int(set_id), int(count)))

        rows: list[ExtremeGearSetBonusBreakpoints] = []
        for breakpoint_set in reduced.sets:
            kept = tuple(
                int(count)
                for count in breakpoint_set.bonus_counts
                if (int(breakpoint_set.set_id), int(count)) not in pruned_pairs
            )
            rows.append(
                ExtremeGearSetBonusBreakpoints(
                    set_id=int(breakpoint_set.set_id),
                    name=breakpoint_set.name,
                    max_equip_count=int(breakpoint_set.max_equip_count),
                    bonus_counts=kept,
                    rejected_bonus_counts=tuple(breakpoint_set.rejected_bonus_counts),
                )
            )

        return (
            ExtremeGearSetBonusBreakpointCatalog(
                sets=tuple(rows),
                unresolved=tuple(reduced.unresolved),
            ),
            len(pruned_pairs),
        )

    def _candidates(
        self,
        frontier: ExtremeGearSetBonusBreakpointCatalog,
    ) -> tuple[dict[int, tuple[_Candidate, ...]], tuple[tuple[int, str, int], ...]]:
        evidence_by_key = {
            (int(row.set_id), int(row.piece_count)): row
            for row in self.relevance.evidence
        }
        eligibility_by_id = {int(row.set_id): row for row in self.eligibility.sets}
        ordinary: dict[int, list[_Candidate]] = {}
        special: list[tuple[int, str, int]] = []

        for breakpoint_set in frontier.sets:
            physical = eligibility_by_id.get(int(breakpoint_set.set_id))
            if physical is None or not physical.has_physical_slot_evidence:
                continue
            for count in breakpoint_set.bonus_counts:
                evidence = evidence_by_key.get((int(breakpoint_set.set_id), int(count)))
                if evidence is None:
                    continue
                delta = self._ordinary_exact_delta(evidence, self.relevance.objective_key)
                if delta is None:
                    if evidence.status is not ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
                        special.append(
                            (int(breakpoint_set.set_id), str(breakpoint_set.name), int(count))
                        )
                    continue
                ordinary.setdefault(int(count), []).append(
                    _Candidate(
                        set_id=int(breakpoint_set.set_id),
                        name=str(breakpoint_set.name),
                        piece_count=int(count),
                        exact_delta=float(delta),
                        eligibility=physical,
                    )
                )

        ordered = {
            count: tuple(
                sorted(
                    rows,
                    key=lambda row: (
                        -row.exact_delta,
                        row.set_id,
                        row.name.casefold(),
                        row.name,
                    ),
                )
            )
            for count, rows in ordinary.items()
        }
        return ordered, tuple(sorted(set(special), key=lambda row: (row[2], row[0], row[1])))

    @staticmethod
    def _stats(**values: int) -> ExtremeOrdinaryNamedGearSearchStats:
        return ExtremeOrdinaryNamedGearSearchStats(**values)

    @staticmethod
    def _distinct_id_remaining_bound(
        *,
        counts: tuple[int, ...],
        position: int,
        candidates_by_count: dict[int, tuple[_Candidate, ...]],
        used_ids: set[int],
    ) -> float | None:
        """Return a proof-safe tighter upper bound for the remaining ordinary score.

        For each remaining breakpoint-count class, take the strongest still-unused
        distinct set IDs needed to fill that class. The same set ID may still be
        counted again in a *different* count class, so this deliberately remains an
        overestimate whenever cross-count identity conflicts exist. Ignoring physical
        conflicts is likewise optimistic. Therefore a finite result is safe for
        branch-and-bound pruning; ``None`` means there are not even enough distinct
        IDs inside one count class to complete the topology.
        """

        remaining_by_count: dict[int, int] = {}
        for count in counts[position:]:
            remaining_by_count[int(count)] = remaining_by_count.get(int(count), 0) + 1

        total = 0.0
        for count, needed in remaining_by_count.items():
            available: list[float] = []
            seen: set[int] = set()
            for row in candidates_by_count.get(int(count), ()):
                if row.set_id in used_ids or row.set_id in seen:
                    continue
                seen.add(row.set_id)
                available.append(float(row.exact_delta))
                if len(available) >= needed:
                    break
            if len(available) < needed:
                return None
            total += sum(available[:needed])
        return float(total)

    def _search_topology(
        self,
        topology: ExtremeGearSetCountTopology,
        candidates_by_count: dict[int, tuple[_Candidate, ...]],
        frontier: ExtremeGearSetBonusBreakpointCatalog,
        *,
        feasibility: ExtremePartialNamedGearPhysicalFeasibilityService,
    ) -> ExtremeOrdinaryNamedGearTopologyWinner:
        counts = tuple(int(value) for value in topology.counts)
        candidate_rows = tuple(candidates_by_count.get(count, ()) for count in counts)
        if any(not rows for rows in candidate_rows):
            return ExtremeOrdinaryNamedGearTopologyWinner(
                topology=topology,
                best_exact_flat_delta=None,
                realizations=(),
                stats=self._stats(),
            )

        realizer = ExtremeNamedGearSetCatalogRealizationService(
            breakpoints=frontier,
            eligibility=self.eligibility,
        )
        selected: list[_Candidate] = []
        used_ids: set[int] = set()
        best = float("-inf")
        winners: list[ExtremeNamedGearSetRealization] = []

        nodes = leaves = witness_checks = feasible_leaves = rejected_leaves = 0
        score_pruned = physical_pruned = 0

        def visit(position: int, score: float) -> None:
            nonlocal best, nodes, leaves, witness_checks, feasible_leaves
            nonlocal rejected_leaves, score_pruned, physical_pruned, winners
            nodes += 1

            remaining_bound = self._distinct_id_remaining_bound(
                counts=counts,
                position=position,
                candidates_by_count=candidates_by_count,
                used_ids=used_ids,
            )
            if remaining_bound is None:
                score_pruned += 1
                return
            if best != float("-inf") and score + remaining_bound < best - 1e-9:
                score_pruned += 1
                return

            if position >= len(counts):
                leaves += 1
                physical = tuple(row.eligibility for row in selected)
                witness_checks += 1
                witness = realizer._find_witness_cached(topology, physical)
                if witness is None:
                    rejected_leaves += 1
                    return
                feasible_leaves += 1
                if score > best + 1e-9:
                    best = score
                    winners = [witness]
                elif abs(score - best) <= 1e-9:
                    winners.append(witness)
                return

            previous_equal_id: int | None = None
            if position > 0 and counts[position - 1] == counts[position]:
                previous_equal_id = selected[position - 1].set_id

            for row in candidate_rows[position]:
                if row.set_id in used_ids:
                    continue
                if previous_equal_id is not None and row.set_id <= previous_equal_id:
                    continue
                selected.append(row)
                used_ids.add(row.set_id)
                physical_prefix = tuple(item.eligibility for item in selected)
                if feasibility.is_possible(topology, physical_prefix):
                    visit(position + 1, score + row.exact_delta)
                else:
                    physical_pruned += 1
                used_ids.remove(row.set_id)
                selected.pop()

        visit(0, 0.0)
        winners.sort(
            key=lambda witness: (
                witness.set_ids,
                witness.weapon_shape.value,
                tuple((row.slot, row.set_id, row.weapon_type) for row in witness.assignments),
            )
        )
        return ExtremeOrdinaryNamedGearTopologyWinner(
            topology=topology,
            best_exact_flat_delta=(None if best == float("-inf") else float(best)),
            realizations=tuple(winners),
            stats=self._stats(
                nodes=nodes,
                leaves=leaves,
                witness_checks=witness_checks,
                feasible_leaves=feasible_leaves,
                rejected_leaves=rejected_leaves,
                score_pruned=score_pruned,
                physical_pruned=physical_pruned,
            ),
        )

    def search(
        self,
        topology_catalog: ExtremeGearSetTopologyCatalog,
    ) -> ExtremeMaxResourceOrdinaryNamedGearSearchResult:
        objective = str(self.relevance.objective_key or "").strip().casefold()
        if objective not in self.SUPPORTED_OBJECTIVES:
            raise ValueError(
                "ordinary named-gear branch-and-bound supports only max-resource objectives"
            )

        reducer = ExtremeObjectiveNamedGearSetCatalogRealizationService(
            breakpoints=self.breakpoints,
            eligibility=self.eligibility,
            relevance=self.relevance,
        )
        reduced, equivalent_pruned, representative_limit = reducer.proof_reduced_breakpoints(
            topology_catalog
        )
        frontier, frontier_pruned = self._frontier(reduced, representative_limit)
        candidates, special = self._candidates(frontier)
        feasibility = ExtremePartialNamedGearPhysicalFeasibilityService()

        winners = tuple(
            self._search_topology(
                topology,
                candidates,
                frontier,
                feasibility=feasibility,
            )
            for topology in topology_catalog.topologies
        )
        unresolved = tuple(
            dict.fromkeys(
                (
                    *topology_catalog.unresolved,
                    *frontier.unresolved,
                    *self.relevance.unresolved,
                )
            )
        )
        return ExtremeMaxResourceOrdinaryNamedGearSearchResult(
            objective_key=objective,
            topologies=winners,
            equivalent_breakpoints_pruned=int(equivalent_pruned),
            frontier_breakpoints_pruned=int(frontier_pruned),
            representative_limit=int(representative_limit),
            special_or_nonflat_pairs=special,
            unresolved=unresolved,
        )


__all__ = [
    "ExtremeMaxResourceOrdinaryNamedGearSearchResult",
    "ExtremeMaxResourceOrdinaryNamedGearSearchService",
    "ExtremeOrdinaryNamedGearSearchStats",
    "ExtremeOrdinaryNamedGearTopologyWinner",
]
