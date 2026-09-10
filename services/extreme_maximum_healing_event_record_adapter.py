from __future__ import annotations

"""Adapt Stage-2 MOST Actual Heal results into the canonical Extreme Record contract.

Stage 2 is deliberately a targeted shortlist search.  This adapter preserves the
numeric leader, its winning build snapshot, setup requirements, unresolved
mechanics, source-supported ceiling threats, and exact search boundary without
ever promoting the result to a globally proven record.
"""

from services.extreme_maximum_heal_unresolved_relevance_service import (
    ExtremeMaximumHealUnresolvedRelevanceService,
)
from services.extreme_maximum_healing_event_finalist_optimization_service import (
    ExtremeMaximumHealingEventFinalistOptimizationResult,
)
from services.extreme_maximum_healing_event_uncertainty_bound_service import (
    ExtremeMaximumHealingEventUncertaintyBoundService,
)
from services.extreme_record_result import (
    ExtremeRecordCeilingThreat,
    ExtremeRecordProofStatus,
    ExtremeRecordResult,
    ExtremeRecordSearchCoverage,
)


class ExtremeMaximumHealingEventRecordAdapter:
    """Project one Stage-2 maximum-healing search into an Extreme Record."""

    def __init__(
        self,
        *,
        relevance: ExtremeMaximumHealUnresolvedRelevanceService | None = None,
        bounds: ExtremeMaximumHealingEventUncertaintyBoundService | None = None,
    ) -> None:
        self.relevance = relevance or ExtremeMaximumHealUnresolvedRelevanceService()
        self.bounds = bounds or ExtremeMaximumHealingEventUncertaintyBoundService()

    @staticmethod
    def _winning_build(leader):
        route_entry = getattr(leader, "route_entry", None)
        optimization = getattr(route_entry, "optimization", None)
        optimized_build = getattr(optimization, "optimized_build", None)
        if optimized_build is not None:
            return optimized_build
        return getattr(route_entry, "candidate_build", None)

    def adapt(
        self,
        result: ExtremeMaximumHealingEventFinalistOptimizationResult,
    ) -> ExtremeRecordResult:
        leader = result.best_scored
        coverage = ExtremeRecordSearchCoverage(
            searched=tuple(result.search_scope),
            omitted=tuple(result.omitted_scope),
            candidates_screened=int(result.selection.screened_scored_entries),
            candidates_optimized=len(result.entries),
            denominator_proven=False,
        )

        if leader is None or leader.event_value is None:
            unresolved = tuple(
                dict.fromkeys(
                    (
                        "Stage-2 maximum-healing search produced no scored leader",
                        *tuple(result.errors),
                    )
                )
            )
            return ExtremeRecordResult.for_objective(
                "actual_heal",
                raw_value=None,
                proof_status=ExtremeRecordProofStatus.UNRESOLVED,
                unresolved=unresolved,
                search_coverage=coverage,
            )

        leader_relevance = self.relevance.classify(leader.unresolved)
        leader_value = float(leader.event_value)
        ceiling_threats: list[ExtremeRecordCeilingThreat] = []
        seen_threats: set[tuple[str, float | None, float | None, str]] = set()
        for entry in result.entries:
            bound = self.bounds.bound(entry)
            if (
                bound.lower_bound is None
                or bound.upper_bound is None
                or bound.upper_bound <= bound.lower_bound + 1e-9
                or bound.upper_bound <= leader_value + 1e-9
            ):
                continue
            threat = ExtremeRecordCeilingThreat(
                source=str(entry.source_name),
                lower_bound=float(bound.lower_bound),
                upper_bound=float(bound.upper_bound),
                reason=str(bound.reason or ""),
            )
            key = (
                threat.source.casefold(),
                threat.lower_bound,
                threat.upper_bound,
                threat.reason,
            )
            if key not in seen_threats:
                seen_threats.add(key)
                ceiling_threats.append(threat)

        unresolved = tuple(
            dict.fromkeys(
                (
                    *leader_relevance.relevant,
                    *tuple(result.errors),
                )
            )
        )
        route = tuple(getattr(leader.route, "equipped_skill_lines", ()) or ())
        explanation = [
            f"Stage-2 numeric leader: {leader.source_name} at {leader_value:.3f} ({leader.event_kind})."
        ]
        if route:
            explanation.append("Winning class-line route: " + ", ".join(route) + ".")
        explanation.append(
            "Stage 2 is a targeted shortlist whole-build search; its denominator is not globally proven."
        )

        return ExtremeRecordResult.for_objective(
            "actual_heal",
            raw_value=leader_value,
            proof_status=ExtremeRecordProofStatus.LOWER_BOUND,
            winning_build=self._winning_build(leader),
            unit="heal",
            runtime_prerequisites=tuple(leader_relevance.setup_prerequisites),
            unresolved=unresolved,
            ceiling_threats=tuple(ceiling_threats),
            search_coverage=coverage,
            explanation=tuple(explanation),
        )
