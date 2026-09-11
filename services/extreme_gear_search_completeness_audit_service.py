from __future__ import annotations

"""Cross-check the canonical denominator feeding Extreme named-gear search.

The individual gear services already prove narrower facts: abstract count topology,
canonical set-bonus breakpoints, physical slot eligibility, and objective relevance.
A global search can only claim a complete named-gear denominator when those layers
refer to the same canonical set universe and every mechanically relevant breakpoint
has explicit objective evidence.

This service owns no gear math and performs no pruning. It is an accounting/proof
layer only; mismatches remain explicit and fail closed.
"""

from dataclasses import dataclass

from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevanceCatalog,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalog
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityCatalog,
)


@dataclass(frozen=True)
class ExtremeGearSearchCompletenessAuditResult:
    objective_key: str
    canonical_sets_reviewed: int
    mechanically_relevant_breakpoints: int
    relevance_breakpoints_reviewed: int
    missing_from_breakpoints: tuple[int, ...] = ()
    missing_from_slot_eligibility: tuple[int, ...] = ()
    extra_breakpoint_sets: tuple[int, ...] = ()
    extra_slot_eligibility_sets: tuple[int, ...] = ()
    missing_relevance_breakpoints: tuple[tuple[int, int], ...] = ()
    extra_relevance_breakpoints: tuple[tuple[int, int], ...] = ()
    candidate_sets_without_slot_evidence: tuple[int, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        return not any(
            (
                self.missing_from_breakpoints,
                self.missing_from_slot_eligibility,
                self.extra_breakpoint_sets,
                self.extra_slot_eligibility_sets,
                self.missing_relevance_breakpoints,
                self.extra_relevance_breakpoints,
                self.candidate_sets_without_slot_evidence,
                self.unresolved,
            )
        )


class ExtremeGearSearchCompletenessAuditService:
    """Prove that every named-gear search layer covers one canonical denominator."""

    @staticmethod
    def build(
        *,
        topology: ExtremeGearSetTopologyCatalog,
        breakpoints: ExtremeGearSetBonusBreakpointCatalog,
        eligibility: ExtremeNamedGearSetSlotEligibilityCatalog,
        relevance: ExtremeGearSetObjectiveRelevanceCatalog,
    ) -> ExtremeGearSearchCompletenessAuditResult:
        canonical_ids = {int(row.set_id) for row in topology.sets}
        breakpoint_ids = {int(row.set_id) for row in breakpoints.sets}
        eligibility_ids = {int(row.set_id) for row in eligibility.sets}

        expected_breakpoints = {
            (int(row.set_id), int(piece_count))
            for row in breakpoints.mechanically_relevant_sets
            for piece_count in row.bonus_counts
        }
        reviewed_breakpoints = {
            (int(row.set_id), int(row.piece_count))
            for row in relevance.evidence
        }

        eligibility_by_id = {int(row.set_id): row for row in eligibility.sets}
        candidate_sets_without_slot_evidence = tuple(
            sorted(
                set_id
                for set_id in relevance.candidate_set_ids
                if (
                    set_id not in eligibility_by_id
                    or not eligibility_by_id[set_id].has_physical_slot_evidence
                )
            )
        )

        unresolved = tuple(
            dict.fromkeys(
                item
                for item in (
                    *topology.unresolved,
                    *breakpoints.unresolved,
                    *eligibility.unresolved,
                    *relevance.unresolved,
                )
                if item
            )
        )

        return ExtremeGearSearchCompletenessAuditResult(
            objective_key=str(relevance.objective_key),
            canonical_sets_reviewed=len(canonical_ids),
            mechanically_relevant_breakpoints=len(expected_breakpoints),
            relevance_breakpoints_reviewed=len(reviewed_breakpoints),
            missing_from_breakpoints=tuple(sorted(canonical_ids - breakpoint_ids)),
            missing_from_slot_eligibility=tuple(sorted(canonical_ids - eligibility_ids)),
            extra_breakpoint_sets=tuple(sorted(breakpoint_ids - canonical_ids)),
            extra_slot_eligibility_sets=tuple(sorted(eligibility_ids - canonical_ids)),
            missing_relevance_breakpoints=tuple(sorted(expected_breakpoints - reviewed_breakpoints)),
            extra_relevance_breakpoints=tuple(sorted(reviewed_breakpoints - expected_breakpoints)),
            candidate_sets_without_slot_evidence=candidate_sets_without_slot_evidence,
            unresolved=unresolved,
        )


__all__ = [
    "ExtremeGearSearchCompletenessAuditResult",
    "ExtremeGearSearchCompletenessAuditService",
]
