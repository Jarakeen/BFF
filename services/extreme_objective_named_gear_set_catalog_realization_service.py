from __future__ import annotations

"""Apply proof-safe objective relevance before catalog-wide named gear realization.

The generic named-set realizer knows which breakpoint counts can physically exist,
but it is objective-neutral. This adapter narrows its breakpoint catalog using the
canonical objective relevance ledger:

* relevant breakpoints remain searchable;
* unresolved breakpoints remain searchable and keep proof open;
* proven-irrelevant breakpoints are removed;
* fully resolved, mechanically identical breakpoint candidates may be represented
  by a bounded set of equivalent named identities.

The equivalence reduction is not cross-set dominance. It only collapses candidates
that have the same requested-objective effect signature and the same physical slot
eligibility, while preserving enough distinct named identities to satisfy every
set-part in any active-snapshot topology. Unresolved candidates and search-space
mutators remain individually searchable.
"""

from dataclasses import dataclass
from typing import Any

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
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalog
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationResult,
    ExtremeNamedGearSetCatalogRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
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
    breakpoints_pruned_equivalent: int = 0
    representative_limit_per_equivalence_class: int = 0
    equivalence_reduction_proven: bool = True
    candidate_reduction_proven: bool = True
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
        return (
            self.equivalence_reduction_proven
            and self.candidate_reduction_proven
            and self.realization.denominator_proven
            and not self.unresolved
        )


class ExtremeObjectiveNamedGearSetCatalogRealizationService:
    """Realize the proof-safe representative named-gear search for an objective."""

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

    @staticmethod
    def _enum_value(value: Any) -> str:
        raw = getattr(value, "value", value)
        return "" if raw is None else str(raw)

    @classmethod
    def _effect_signature(cls, effect: Any) -> tuple[Any, ...]:
        """Identity-free mechanic signature for one requested-objective effect."""

        return (
            cls._enum_value(getattr(effect, "stat", None)),
            cls._enum_value(getattr(effect, "operation", None)),
            float(getattr(effect, "value", 0.0)),
            cls._enum_value(getattr(effect, "kind", None)),
            cls._enum_value(getattr(effect, "unit", None)),
            str(getattr(effect, "damage_type", None) or ""),
            str(getattr(effect, "target", None) or ""),
            (
                None
                if getattr(effect, "duration_value", None) is None
                else float(getattr(effect, "duration_value"))
            ),
            str(getattr(effect, "duration_unit", None) or ""),
            str(getattr(effect, "condition", None) or ""),
        )

    @staticmethod
    def _eligibility_signature(
        row: ExtremeNamedGearSetSlotEligibility,
    ) -> tuple[Any, ...]:
        """Everything the named witness solver can use to distinguish two sets."""

        return (
            str(row.category or "").strip().casefold(),
            int(row.max_equip_count),
            tuple(row.armor_slots),
            tuple(row.jewelry_slots),
            tuple(row.weapon_types),
            tuple(row.synthetic_weapon_types),
            tuple(int(value) for value in row.other_equip_types),
        )

    def _equivalence_key(
        self,
        evidence: ExtremeGearSetObjectiveBreakpointEvidence,
        eligibility: ExtremeNamedGearSetSlotEligibility | None,
    ) -> tuple[Any, ...] | None:
        """Return a proof-safe interchangeability key, or None to keep identity.

        We deliberately refuse to collapse unresolved candidates or reviewed search
        state mutators. Those cases may depend on identity-specific execution later.
        For ordinary mechanic-complete candidates, only effects that target the
        requested objective need to distinguish representatives; other mapped or
        screened effects have already been proven irrelevant to this objective by
        the relevance layer.
        """

        if evidence.status is not ExtremeGearSetObjectiveRelevance.RELEVANT:
            return None
        if evidence.search_state_rule is not None:
            return None
        if evidence.candidate.unresolved:
            return None
        if eligibility is None or not eligibility.has_physical_slot_evidence:
            return None

        target_stats = ExtremeGearSetObjectiveService._target_stats(
            self.relevance.objective_key
        )
        relevant_effects = tuple(
            sorted(
                self._effect_signature(effect)
                for effect in evidence.candidate.source_effects
                if effect.stat in target_stats
            )
        )
        if not relevant_effects:
            return None

        return (
            int(evidence.piece_count),
            self._eligibility_signature(eligibility),
            relevant_effects,
            float(evidence.reviewed_delta),
        )

    def proof_reduced_breakpoints(
        self,
        topology_catalog: ExtremeGearSetTopologyCatalog,
    ) -> tuple[ExtremeGearSetBonusBreakpointCatalog, int, int]:
        """Collapse only provably interchangeable named identities.

        A topology cannot contain more distinct set identities than it has set
        parts. Retaining that many named representatives from every equivalence
        class is therefore sufficient to preserve all distinct-identity feasibility,
        including overlap between different breakpoint-count classes.
        """

        filtered = self._filtered_breakpoints()
        representative_limit = max(
            (len(topology.counts) for topology in topology_catalog.topologies),
            default=1,
        )
        representative_limit = max(1, int(representative_limit))

        evidence_by_key = {
            (int(row.set_id), int(row.piece_count)): row
            for row in self.relevance.evidence
        }
        eligibility_by_id = {
            int(row.set_id): row
            for row in self.eligibility.sets
        }

        groups: dict[tuple[Any, ...], list[tuple[int, str, int]]] = {}
        for breakpoint_set in filtered.sets:
            for count in breakpoint_set.bonus_counts:
                pair = (int(breakpoint_set.set_id), int(count))
                evidence = evidence_by_key.get(pair)
                if evidence is None:
                    continue
                key = self._equivalence_key(
                    evidence,
                    eligibility_by_id.get(int(breakpoint_set.set_id)),
                )
                if key is None:
                    continue
                groups.setdefault(key, []).append(
                    (
                        int(breakpoint_set.set_id),
                        str(breakpoint_set.name),
                        int(count),
                    )
                )

        pruned_pairs: set[tuple[int, int]] = set()
        for members in groups.values():
            ordered = tuple(
                sorted(
                    members,
                    key=lambda item: (item[0], item[1].casefold(), item[1], item[2]),
                )
            )
            for set_id, _name, count in ordered[representative_limit:]:
                pruned_pairs.add((int(set_id), int(count)))

        if not pruned_pairs:
            return filtered, 0, representative_limit

        reduced_rows: list[ExtremeGearSetBonusBreakpoints] = []
        for breakpoint_set in filtered.sets:
            kept = tuple(
                int(count)
                for count in breakpoint_set.bonus_counts
                if (int(breakpoint_set.set_id), int(count)) not in pruned_pairs
            )
            reduced_rows.append(
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
                sets=tuple(reduced_rows),
                unresolved=tuple(filtered.unresolved),
            ),
            len(pruned_pairs),
            representative_limit,
        )

    def build(
        self,
        topology_catalog: ExtremeGearSetTopologyCatalog,
        *,
        max_assignments_per_topology: int | None = None,
    ) -> ExtremeObjectiveNamedGearSetCatalogRealizationResult:
        objective = str(self.relevance.objective_key or "").strip().casefold()
        if objective == "max_health" and max_assignments_per_topology is None:
            # Local imports avoid an import cycle: the Max Health frontier reuses
            # this service's proof-reduction helpers but only calls them after this
            # module is fully initialized.
            from services.extreme_max_health_named_gear_candidate_search_service import (
                ExtremeMaxHealthNamedGearCandidateSearchService,
            )
            from services.extreme_max_health_named_gear_realization_adapter_service import (
                ExtremeMaxHealthNamedGearRealizationAdapterService,
            )
            from services.extreme_max_resource_ordinary_named_gear_search_service import (
                ExtremeMaxResourceOrdinaryNamedGearSearchService,
            )

            ordinary = ExtremeMaxResourceOrdinaryNamedGearSearchService(
                breakpoints=self.breakpoints,
                eligibility=self.eligibility,
                relevance=self.relevance,
            )
            candidate_search = ExtremeMaxHealthNamedGearCandidateSearchService(
                ordinary_service=ordinary,
                eligibility=self.eligibility,
            ).search(topology_catalog)
            return ExtremeMaxHealthNamedGearRealizationAdapterService.build(
                search=candidate_search,
                topology_catalog=topology_catalog,
                relevance=self.relevance,
            )

        reduced, equivalent_pruned, representative_limit = self.proof_reduced_breakpoints(
            topology_catalog
        )
        realizer = ExtremeNamedGearSetCatalogRealizationService(
            breakpoints=reduced,
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
                    *reduced.unresolved,
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
            breakpoints_pruned_equivalent=equivalent_pruned,
            representative_limit_per_equivalence_class=representative_limit,
            equivalence_reduction_proven=True,
            candidate_reduction_proven=True,
            unresolved=unresolved,
        )
