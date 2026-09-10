from __future__ import annotations

"""Adapt route-wide critical-heal searches into the canonical Extreme Record contract.

The ordinary healing route catalog is already ranked by canonical ``critical_heal``
values.  This adapter deliberately consumes that ordinary-heal catalog rather
than the broader MOST Actual Heal aggregator because explicitly non-crittable
families (for example Blood Magic) are valid Actual Heal candidates but must
never enter the Critical Heal leaderboard.
"""

from services.extreme_actual_heal_class_route_catalog_service import (
    ExtremeActualHealClassRouteCatalogResult,
)
from services.extreme_maximum_heal_unresolved_relevance_service import (
    ExtremeMaximumHealUnresolvedRelevanceService,
)
from services.extreme_record_result import (
    ExtremeRecordProofStatus,
    ExtremeRecordResult,
    ExtremeRecordSearchCoverage,
)


class ExtremeCriticalHealRecordAdapter:
    """Project one critical-heal class-route search into an Extreme Record."""

    def __init__(
        self,
        *,
        relevance: ExtremeMaximumHealUnresolvedRelevanceService | None = None,
    ) -> None:
        self.relevance = relevance or ExtremeMaximumHealUnresolvedRelevanceService()

    @staticmethod
    def _winning_build(leader):
        optimization = getattr(leader, "optimization", None)
        optimized_build = getattr(optimization, "optimized_build", None)
        if optimized_build is not None:
            return optimized_build
        return getattr(leader, "candidate_build", None)

    def adapt(self, result: ExtremeActualHealClassRouteCatalogResult) -> ExtremeRecordResult:
        leader = result.best_scored
        entries = tuple(result.entries)
        optimized_count = sum(
            1 for entry in entries if getattr(entry, "optimization", None) is not None
        )
        denominator_proven = bool(result.global_maximum_proven)
        coverage = ExtremeRecordSearchCoverage(
            searched=tuple(result.search_scope),
            omitted=tuple(result.omitted_scope),
            candidates_screened=len(entries),
            candidates_optimized=optimized_count,
            denominator_proven=denominator_proven,
        )

        if leader is None or leader.critical_heal is None:
            return ExtremeRecordResult.for_objective(
                "critical_heal",
                raw_value=None,
                proof_status=ExtremeRecordProofStatus.UNRESOLVED,
                unresolved=("Critical-heal route search produced no scored critical event",),
                search_coverage=coverage,
            )

        value = float(leader.critical_heal)
        classified = self.relevance.classify(leader.unresolved)
        status = (
            ExtremeRecordProofStatus.PROVEN
            if denominator_proven and leader.mechanic_complete and not classified.relevant
            else ExtremeRecordProofStatus.LOWER_BOUND
        )

        route = tuple(getattr(leader.route, "equipped_skill_lines", ()) or ())
        candidate = getattr(leader, "candidate", None)
        ability_name = str(getattr(candidate, "name", "") or "critical-heal candidate")
        explanation = [
            f"Current critical-heal leader: {ability_name} at {value:.3f}.",
            "Only canonically critical-capable ordinary healing events participate in this record.",
        ]
        if route:
            explanation.append("Winning class-line route: " + ", ".join(route) + ".")
        if not denominator_proven:
            explanation.append(
                "The searched denominator is not globally proven; this value remains a lower bound."
            )

        return ExtremeRecordResult.for_objective(
            "critical_heal",
            raw_value=value,
            proof_status=status,
            winning_build=self._winning_build(leader),
            unit="heal",
            runtime_prerequisites=tuple(classified.setup_prerequisites),
            unresolved=tuple(classified.relevant),
            search_coverage=coverage,
            explanation=tuple(explanation),
        )
