from __future__ import annotations

"""Add the finite Mundus axis to structural Extreme core-stat search.

This service composes, rather than replaces, the existing structural search.
For every race × legal class route × 64-point attribute allocation × active-bar
candidate it evaluates every canonical Update-50 Mundus Stone plus the legal
no-Mundus baseline through the same canonical stat evaluator.

Closing this axis is useful denominator progress, but it does not promote the
record to global proof while gear, skills, CP, consumables, runtime state, and
other dynamic axes remain deferred.
"""

from pathlib import Path
from typing import Any

from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from services.extreme_core_stat_record_service import ExtremeCoreStatRecordService
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_hypothetical_class_progression_service import (
    ExtremeHypotheticalClassProgressionService,
)
from services.extreme_optimization_service import ExtremeOptimizationService
from services.extreme_record_result import (
    ExtremeRecordProofStatus,
    ExtremeRecordResult,
    ExtremeRecordSearchCoverage,
)
from services.extreme_structural_core_stat_record_service import (
    ExtremeCanonicalStructuralStatEvaluator,
    ExtremeStructuralCoreStatRecordService,
)
from services.extreme_structural_global_search_service import (
    ExtremeStructuralCandidate,
    ExtremeStructuralGlobalSearchResult,
    ExtremeStructuralGlobalSearchService,
)


_MUNDUS_DEFERRED_AXIS = "Mundus"
_MUNDUS_SCOPE = "all canonical Update-50 Mundus Stone choices plus no-Mundus baseline"


class ExtremeBestMundusStructuralStatEvaluator:
    """Score every legal Mundus choice for one structural candidate."""

    def __init__(
        self,
        *,
        evaluator: ExtremeCanonicalStructuralStatEvaluator,
        mundus_repository: MundusRepository,
    ) -> None:
        self.evaluator = evaluator
        self.mundus_repository = mundus_repository

    def mundus_choices(self) -> tuple[str, ...]:
        # Empty string is a real legal baseline: a character may have no stone.
        # Exact-name dedupe preserves canonical repository spelling/order.
        values: list[str] = [""]
        seen = {""}
        for raw in self.mundus_repository.list_names():
            name = str(raw or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            values.append(name)
        return tuple(values)

    def __call__(
        self,
        objective_key: str,
        candidate: ExtremeStructuralCandidate,
    ) -> tuple[float, dict[str, Any], tuple[str, ...]]:
        best_value: float | None = None
        best_payload: dict[str, Any] | None = None
        best_unresolved: tuple[str, ...] = ()
        best_mundus = ""

        for mundus in self.mundus_choices():
            value, payload, unresolved = self.evaluator.evaluate_candidate(
                objective_key,
                candidate,
                mundus=mundus,
            )
            score = float(value)
            if (
                best_value is None
                or score > best_value + 1e-9
                or (
                    abs(score - best_value) <= 1e-9
                    and mundus.casefold() < best_mundus.casefold()
                )
            ):
                best_value = score
                best_payload = payload
                best_unresolved = tuple(unresolved or ())
                best_mundus = mundus

        if best_value is None or best_payload is None:
            raise ValueError("Extreme Mundus search produced no legal Mundus candidate")
        return best_value, best_payload, best_unresolved


class ExtremeStructuralMundusCoreStatRecordService:
    """Return structural + Mundus lower bounds for executable core records."""

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        optimizer: ExtremeOptimizationService | None = None,
        search_service: ExtremeStructuralGlobalSearchService[dict[str, Any]] | None = None,
        mundus_evaluator: ExtremeBestMundusStructuralStatEvaluator | None = None,
    ) -> None:
        self.optimizer = optimizer or ExtremeOptimizationService(database_path=database_path)
        resolved_database = Path(database_path or self.optimizer.database_path)

        if mundus_evaluator is None:
            canonical = ExtremeCanonicalStructuralStatEvaluator(
                optimizer=self.optimizer,
                progression_service=ExtremeHypotheticalClassProgressionService(resolved_database),
            )
            mundus_evaluator = ExtremeBestMundusStructuralStatEvaluator(
                evaluator=canonical,
                mundus_repository=MundusRepository(
                    resolved_database,
                    game_update=U50_GAME_UPDATE,
                    initialize=False,
                ),
            )
        self.mundus_evaluator = mundus_evaluator

        self.search_service = search_service or ExtremeStructuralGlobalSearchService(
            ExtremeGlobalSearchUniverseService(resolved_database),
            scorer=self.mundus_evaluator,
        )

    def record(self, objective_key: str) -> ExtremeRecordResult:
        key = str(objective_key or "").strip().casefold()
        if not ExtremeCoreStatRecordService.supports(key):
            raise ValueError(
                f"Extreme structural+Mundus core-stat search does not support objective: {objective_key!r}"
            )

        result: ExtremeStructuralGlobalSearchResult[dict[str, Any]] = self.search_service.search(key)
        choices = self.mundus_evaluator.mundus_choices()
        searched = tuple((*result.structural_scope, _MUNDUS_SCOPE))
        omitted = tuple(
            axis for axis in result.deferred_dynamic_axes if axis != _MUNDUS_DEFERRED_AXIS
        )
        expanded_count = int(result.candidates_scored) * len(choices)
        denominator_proven = bool(
            result.structural_denominator_proven
            and choices
            and not omitted
        )
        coverage = ExtremeRecordSearchCoverage(
            searched=searched,
            omitted=omitted,
            candidates_screened=expanded_count,
            candidates_optimized=expanded_count,
            denominator_proven=denominator_proven,
        )

        if result.best is None:
            return ExtremeRecordResult.for_objective(
                key,
                raw_value=None,
                proof_status=ExtremeRecordProofStatus.UNRESOLVED,
                unresolved=tuple(
                    dict.fromkeys(
                        (
                            "Structural + Mundus Extreme search produced no scored candidate",
                            *result.unresolved,
                        )
                    )
                ),
                search_coverage=coverage,
            )

        winner = result.best
        winner_mundus = ""
        if isinstance(winner.payload, dict):
            winner_mundus = str(winner.payload.get("mundus") or "")
        explanation = (
            "Exhaustively searched race × legal class/subclass route × all 64-point attribute allocations × active bar × every Update-50 Mundus choice.",
            f"Evaluated {expanded_count:,} structural/Mundus combinations across {len(choices):,} Mundus states including no-Mundus.",
            f"Winning Mundus: {winner_mundus or 'none'}.",
            "Other dynamic axes remain deferred, so this is not yet a globally proven Extreme Record.",
        )
        return ExtremeRecordResult.for_objective(
            key,
            raw_value=float(winner.value),
            proof_status=(
                ExtremeRecordProofStatus.PROVEN
                if denominator_proven and not result.unresolved
                else ExtremeRecordProofStatus.LOWER_BOUND
            ),
            winning_build=winner.payload,
            unit=ExtremeStructuralCoreStatRecordService._unit(key),
            unresolved=tuple(result.unresolved),
            search_coverage=coverage,
            explanation=explanation,
        )
