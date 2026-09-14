from __future__ import annotations

"""Shared exact-flat named-gear search with mandatory named-set constraints.

This layer deliberately reuses the existing production branch-and-bound search.
It adds only one orthogonal requirement: one or more exact named-set breakpoints
must be present in the winning witness.  Required sets that are proven irrelevant
to the requested objective remain legal zero-delta carriers; required sets with
unresolved, conditional, or non-flat requested-objective effects fail closed.

The constraint is encoded as a derived lexicographic search bonus whose magnitude
is computed from the canonical objective frontier.  The bonus is removed before
results leave this service, so it never becomes objective math.
"""

from dataclasses import dataclass, replace

from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
    ExtremeGearSetBonusBreakpoints,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveBreakpointEvidence,
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceCatalog,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalog
from services.extreme_max_resource_ordinary_named_gear_search_service import (
    ExtremeMaxResourceOrdinaryNamedGearSearchResult,
    ExtremeMaxResourceOrdinaryNamedGearSearchService,
    _Candidate,
)
from services.extreme_named_gear_set_realization_service import ExtremeNamedGearSetRealization
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
    ExtremeNamedGearSetSlotEligibilityCatalog,
)


@dataclass(frozen=True)
class ExtremeNamedGearRequirement:
    set_name: str
    piece_count: int


@dataclass(frozen=True)
class ExtremeConstrainedNamedGearExactFlatSearchResult:
    objective_key: str
    requirements: tuple[ExtremeNamedGearRequirement, ...]
    best_exact_flat_delta: float | None
    realizations: tuple[ExtremeNamedGearSetRealization, ...]
    base_search: ExtremeMaxResourceOrdinaryNamedGearSearchResult | None
    special_or_nonflat_pairs: tuple[tuple[int, str, int], ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def winner_found(self) -> bool:
        return self.best_exact_flat_delta is not None and bool(self.realizations)

    @property
    def exact_flat_branch_proven(self) -> bool:
        return not self.unresolved

    @property
    def full_named_gear_denominator_proven(self) -> bool:
        return self.exact_flat_branch_proven and not self.special_or_nonflat_pairs


class ExtremeConstrainedNamedGearExactFlatSearchService(
    ExtremeMaxResourceOrdinaryNamedGearSearchService
):
    """Reuse canonical exact-flat search while requiring named-set breakpoints."""

    SUPPORTED_OBJECTIVES = frozenset(
        (*ExtremeMaxResourceOrdinaryNamedGearSearchService.SUPPORTED_OBJECTIVES, "health_recovery")
    )

    def __init__(
        self,
        *,
        breakpoints: ExtremeGearSetBonusBreakpointCatalog,
        eligibility: ExtremeNamedGearSetSlotEligibilityCatalog,
        relevance: ExtremeGearSetObjectiveRelevanceCatalog,
        requirements: tuple[ExtremeNamedGearRequirement, ...],
    ) -> None:
        super().__init__(
            breakpoints=breakpoints,
            eligibility=eligibility,
            relevance=relevance,
        )
        self.requirements = tuple(requirements)
        self._constraint_bonus = 0.0
        self._resolved_requirements: tuple[
            tuple[ExtremeNamedGearRequirement, ExtremeNamedGearSetSlotEligibility, ExtremeGearSetObjectiveBreakpointEvidence],
            ...
        ] = ()

    def _resolve_requirements(self) -> tuple[str, ...]:
        by_name: dict[str, list[ExtremeNamedGearSetSlotEligibility]] = {}
        for row in self.eligibility.sets:
            by_name.setdefault(row.name.strip().casefold(), []).append(row)
        evidence_by_key = {
            (int(row.set_id), int(row.piece_count)): row
            for row in self.relevance.evidence
        }

        resolved: list[
            tuple[ExtremeNamedGearRequirement, ExtremeNamedGearSetSlotEligibility, ExtremeGearSetObjectiveBreakpointEvidence]
        ] = []
        unresolved: list[str] = []
        seen_ids: set[int] = set()
        for requirement in self.requirements:
            name = str(requirement.set_name or "").strip()
            count = int(requirement.piece_count)
            matches = tuple(by_name.get(name.casefold(), ()))
            if len(matches) != 1:
                unresolved.append(
                    f"Required named set {name!r} resolved to {len(matches)} canonical eligibility rows"
                )
                continue
            physical = matches[0]
            if int(physical.set_id) in seen_ids:
                unresolved.append(f"Required named set repeated: {name!r}")
                continue
            seen_ids.add(int(physical.set_id))
            evidence = evidence_by_key.get((int(physical.set_id), count))
            if evidence is None:
                unresolved.append(
                    f"Required named set {name!r} has no {count}-piece objective evidence"
                )
                continue
            if evidence.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
                pass
            elif self._ordinary_exact_delta(evidence, self.relevance.objective_key) is None:
                unresolved.append(
                    f"Required named set {name!r} {count}pc has non-flat or unresolved "
                    f"{self.relevance.objective_key} semantics"
                )
                continue
            resolved.append((requirement, physical, evidence))

        self._resolved_requirements = tuple(resolved)
        return tuple(dict.fromkeys(unresolved))

    def _frontier(
        self,
        reduced: ExtremeGearSetBonusBreakpointCatalog,
        representative_limit: int,
    ) -> tuple[ExtremeGearSetBonusBreakpointCatalog, int]:
        frontier, pruned = super()._frontier(reduced, representative_limit)
        if not self._resolved_requirements:
            return frontier, pruned

        required_counts = {
            int(physical.set_id): int(requirement.piece_count)
            for requirement, physical, _evidence in self._resolved_requirements
        }
        original_by_id = {int(row.set_id): row for row in self.breakpoints.sets}
        rows: list[ExtremeGearSetBonusBreakpoints] = []
        seen_ids: set[int] = set()
        for row in frontier.sets:
            set_id = int(row.set_id)
            seen_ids.add(set_id)
            required_count = required_counts.get(set_id)
            if required_count is None:
                rows.append(row)
                continue
            kept = tuple(sorted(set((*row.bonus_counts, required_count))))
            rows.append(replace(row, bonus_counts=kept))

        for set_id, required_count in required_counts.items():
            if set_id in seen_ids:
                continue
            original = original_by_id.get(set_id)
            if original is None:
                continue
            rows.append(
                replace(
                    original,
                    bonus_counts=(required_count,),
                )
            )
        rows.sort(key=lambda row: (int(row.set_id), row.name.casefold(), row.name))
        return (
            ExtremeGearSetBonusBreakpointCatalog(
                sets=tuple(rows),
                unresolved=tuple(frontier.unresolved),
            ),
            pruned,
        )

    def _candidates(
        self,
        frontier: ExtremeGearSetBonusBreakpointCatalog,
    ) -> tuple[dict[int, tuple[_Candidate, ...]], tuple[tuple[int, str, int], ...]]:
        ordinary, special = super()._candidates(frontier)
        mutable = {count: list(rows) for count, rows in ordinary.items()}
        required_pairs: set[tuple[int, int]] = set()

        for requirement, physical, evidence in self._resolved_requirements:
            count = int(requirement.piece_count)
            set_id = int(physical.set_id)
            required_pairs.add((set_id, count))
            base_delta = self._ordinary_exact_delta(evidence, self.relevance.objective_key)
            if evidence.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
                base_delta = 0.0
            if base_delta is None:
                continue
            rows = mutable.setdefault(count, [])
            replacement = _Candidate(
                set_id=set_id,
                name=physical.name,
                piece_count=count,
                exact_delta=float(base_delta) + self._constraint_bonus,
                eligibility=physical,
                objective_effect_signature=(
                    ()
                    if evidence.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT
                    else self._objective_effect_signature(evidence, self.relevance.objective_key)
                ),
            )
            rows[:] = [row for row in rows if int(row.set_id) != set_id]
            rows.append(replacement)

        ordered = {
            count: tuple(
                sorted(
                    rows,
                    key=lambda row: (-row.exact_delta, row.set_id, row.name.casefold(), row.name),
                )
            )
            for count, rows in mutable.items()
        }
        filtered_special = tuple(
            row for row in special if (int(row[0]), int(row[2])) not in required_pairs
        )
        return ordered, filtered_special

    @staticmethod
    def _witness_pairs(
        witness: ExtremeNamedGearSetRealization,
    ) -> frozenset[tuple[int, int]]:
        return frozenset(
            (int(set_id), int(count))
            for set_id, count in zip(witness.set_ids, witness.counts)
        )

    def search(
        self,
        topology_catalog: ExtremeGearSetTopologyCatalog,
    ) -> ExtremeConstrainedNamedGearExactFlatSearchResult:
        unresolved = list(self._resolve_requirements())
        objective = str(self.relevance.objective_key or "").strip().casefold()
        if objective not in self.SUPPORTED_OBJECTIVES:
            unresolved.append(f"Unsupported exact-flat objective: {objective!r}")
        if unresolved:
            return ExtremeConstrainedNamedGearExactFlatSearchResult(
                objective_key=objective,
                requirements=self.requirements,
                best_exact_flat_delta=None,
                realizations=(),
                base_search=None,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        max_parts = max((len(row.counts) for row in topology_catalog.topologies), default=1)
        positive_deltas = tuple(
            float(delta)
            for evidence in self.relevance.evidence
            for delta in (self._ordinary_exact_delta(evidence, objective),)
            if delta is not None and float(delta) > 0.0
        )
        maximum_single_delta = max(positive_deltas, default=0.0)
        self._constraint_bonus = 1.0 + float(max_parts) * maximum_single_delta

        base = super().search(topology_catalog)
        required_pairs = frozenset(
            (int(physical.set_id), int(requirement.piece_count))
            for requirement, physical, _evidence in self._resolved_requirements
        )
        bonus_total = self._constraint_bonus * len(required_pairs)

        best: float | None = None
        winners: list[ExtremeNamedGearSetRealization] = []
        for topology in base.topologies:
            if not topology.winner_found or topology.best_exact_flat_delta is None:
                continue
            matching = tuple(
                witness
                for witness in topology.realizations
                if required_pairs.issubset(self._witness_pairs(witness))
            )
            if not matching:
                continue
            actual = float(topology.best_exact_flat_delta) - bonus_total
            if best is None or actual > best + 1e-9:
                best = actual
                winners = list(matching)
            elif abs(actual - best) <= 1e-9:
                winners.extend(matching)

        unique: dict[tuple[object, ...], ExtremeNamedGearSetRealization] = {}
        for witness in winners:
            key = (
                witness.topology_signature,
                witness.set_ids,
                witness.counts,
                witness.weapon_shape.value,
                tuple((row.slot, row.set_id, row.weapon_type) for row in witness.assignments),
            )
            unique[key] = witness

        return ExtremeConstrainedNamedGearExactFlatSearchResult(
            objective_key=objective,
            requirements=self.requirements,
            best_exact_flat_delta=best,
            realizations=tuple(unique[key] for key in sorted(unique, key=repr)),
            base_search=base,
            special_or_nonflat_pairs=tuple(base.special_or_nonflat_pairs),
            unresolved=tuple(base.unresolved),
        )


__all__ = [
    "ExtremeNamedGearRequirement",
    "ExtremeConstrainedNamedGearExactFlatSearchResult",
    "ExtremeConstrainedNamedGearExactFlatSearchService",
]
