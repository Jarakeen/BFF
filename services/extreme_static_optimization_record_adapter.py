from __future__ import annotations

"""Project legacy/static Extreme optimization results into canonical records.

The static optimizer is useful evidence, but it intentionally searches only a
bounded mutation space around one build.  This adapter therefore never upgrades
such a result to a globally proven Extreme Record.  It preserves the winning
build/value and exposes the optimizer's own search/omission boundaries so later
record services and Comp Maker can consume the evidence without overstating it.
"""

from services.extreme_optimization_service import ExtremeOptimizationResult
from services.extreme_record_result import (
    ExtremeRecordProofStatus,
    ExtremeRecordResult,
    ExtremeRecordSearchCoverage,
)


_RATIO_KEYS = frozenset(
    {
        "weapon_critical",
        "spell_critical",
        "critical_damage",
        "healing_done",
    }
)
_RATING_KEYS = frozenset(
    {
        "health_recovery",
        "magicka_recovery",
        "stamina_recovery",
    }
)


class ExtremeStaticOptimizationRecordAdapter:
    """Convert one bounded static optimization result to an Extreme Record."""

    @staticmethod
    def _unit(objective_key: str) -> str:
        if objective_key in _RATIO_KEYS:
            return "ratio"
        if objective_key in _RATING_KEYS:
            return "rating"
        return "points"

    def adapt(self, result: ExtremeOptimizationResult) -> ExtremeRecordResult:
        key = str(result.objective.key).strip().casefold()
        raw_value = float(result.optimized_value)
        unresolved = tuple(dict.fromkeys(message for message in result.unresolved if message))
        searched = tuple(dict.fromkeys(str(item) for item in result.search_scope if item))
        omitted = tuple(dict.fromkeys(str(item) for item in result.omitted_scope if item))

        winning_build = result.optimized_build
        if hasattr(winning_build, "to_dict"):
            winning_build = winning_build.to_dict()

        explanation = (
            "Projected from the bounded static Extreme optimizer.",
            "This is a mechanically evaluated lower bound, not a global record proof, because the static optimizer does not enumerate the complete legal character universe.",
        )

        return ExtremeRecordResult.for_objective(
            key,
            raw_value=raw_value,
            proof_status=ExtremeRecordProofStatus.LOWER_BOUND,
            winning_build=winning_build,
            unit=self._unit(key),
            unresolved=unresolved,
            search_coverage=ExtremeRecordSearchCoverage(
                searched=searched,
                omitted=omitted,
                denominator_proven=False,
            ),
            explanation=explanation,
        )
