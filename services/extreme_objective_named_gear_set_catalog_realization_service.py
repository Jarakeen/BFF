from __future__ import annotations

"""Apply proof-safe objective relevance before catalog-wide named gear realization.

The generic named-set realizer knows which breakpoint counts can physically exist,
but it is objective-neutral.  This adapter narrows its breakpoint catalog using the
canonical objective relevance ledger:

* relevant breakpoints remain searchable;
* unresolved breakpoints remain searchable and keep proof open;
* only proven-irrelevant breakpoints are removed.

No cross-set dominance is inferred here.  Slot cost and coexistence make a simple
larger-delta comparison unsafe until a later Pareto layer proves it explicitly.
"""

from dataclasses import dataclass

from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
    ExtremeGearSetBonusBreakpoints,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceCatalog,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalog
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationResult,
    ExtremeNamedGearSetCatalogRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityCatalog,
)


@dataclass(frozen=True)
class ExtremeObjectiveNamedGearSetCatalogRealizationResult:
    objective_key: str
    realization: ExtremeNamedGearSetCatalogRealizationResult
    breakpoints_reviewed: int
    breakpoints_retained_relevant: int
    breakpoints_retained_unresolved: int
    breakpoints_pruned_irrelevant: int
    unresolved: tuple[str, ...] = ()

    @property
    def assignments_considered(self) -> int:
        return self.realization.assignments_considered

    @property
    def assignments_realized(self) -> int:
        return self.realization.assignments_realized

    @property
    def assignments_rejected(self) -> int:
        return self.realization.assignments_rejected

    @property
    def truncated(self) -> bool:
        return self.realization.truncated

    @property
    def denominator_proven(self) -> bool:
        return self.realization.denominator_proven and not self.unresolved


class ExtremeObjectiveNamedGearSetCatalogRealizationService:
    """Realize only breakpoint states that cannot be safely pruned for an objective."""

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

    def _filtered_breakpoints(self) -> ExtremeGearSetBonusBreakpointCatalog:
        evidence_by_key = {
            (int(row.set_id), int(row.piece_count)): row
            for row in self.relevance.evidence
        }
        rows: list[ExtremeGearSetBonusBreakpoints] = []
        unresolved: list[str] = list(self.breakpoints.unresolved)
        unresolved.extend(self.relevance.unresolved)

        for breakpoint_set in self.breakpoints.sets:
            kept: list[int] = []
            for count in breakpoint_set.bonus_counts:
                evidence = evidence_by_key.get((int(breakpoint_set.set_id), int(count)))
                if evidence is None:
                    unresolved.append(
                        f"Gear set {breakpoint_set.name} breakpoint {count} has no objective relevance evidence for {self.relevance.objective_key}"
                    )
                    kept.append(int(count))
                    continue
                if evidence.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
                    continue
                kept.append(int(count))

            rows.append(
                ExtremeGearSetBonusBreakpoints(
                    set_id=int(breakpoint_set.set_id),
                    name=breakpoint_set.name,
                    max_equip_count=int(breakpoint_set.max_equip_count),
                    bonus_counts=tuple(kept),
                    rejected_bonus_counts=tuple(breakpoint_set.rejected_bonus_counts),
                )
            )

        return ExtremeGearSetBonusBreakpointCatalog(
            sets=tuple(rows),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )

    def build(
        self,
        topology_catalog: ExtremeGearSetTopologyCatalog,
        *,
        max_assignments_per_topology: int | None = None,
    ) -> ExtremeObjectiveNamedGearSetCatalogRealizationResult:
        filtered = self._filtered_breakpoints()
        realizer = ExtremeNamedGearSetCatalogRealizationService(
            breakpoints=filtered,
            eligibility=self.eligibility,
        )
        realization = realizer.build(
            topology_catalog,
            max_assignments_per_topology=max_assignments_per_topology,
        )

        relevant = sum(
            1
            for row in self.relevance.evidence
            if row.status is ExtremeGearSetObjectiveRelevance.RELEVANT
        )
        unresolved_count = sum(
            1
            for row in self.relevance.evidence
            if row.status is ExtremeGearSetObjectiveRelevance.UNRESOLVED
        )
        pruned = sum(
            1
            for row in self.relevance.evidence
            if row.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT
        )
        unresolved = tuple(
            dict.fromkeys(
                (
                    *self.relevance.unresolved,
                    *filtered.unresolved,
                    *realization.unresolved,
                )
            )
        )
        return ExtremeObjectiveNamedGearSetCatalogRealizationResult(
            objective_key=self.relevance.objective_key,
            realization=realization,
            breakpoints_reviewed=len(self.relevance.evidence),
            breakpoints_retained_relevant=relevant,
            breakpoints_retained_unresolved=unresolved_count,
            breakpoints_pruned_irrelevant=pruned,
            unresolved=unresolved,
        )
