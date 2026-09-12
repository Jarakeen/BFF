from __future__ import annotations

"""Add the finite Mundus axis to structural Extreme core-stat search.

This service composes, rather than replaces, the existing structural search.
For ordinary objectives every canonical Update-50 Mundus Stone plus the legal
no-Mundus baseline remains exhaustive. Max Magicka / Max Stamina may use the
proof-owned resource Mundus projection when the canonical catalogue proves a
unique dominant target-resource witness.
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
from services.extreme_resource_mundus_projection_service import (
    ExtremeResourceMundusProjection,
    ExtremeResourceMundusProjectionService,
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
    """Score legal Mundus choices, using proof reductions for max resources."""

    def __init__(
        self,
        *,
        evaluator: ExtremeCanonicalStructuralStatEvaluator,
        mundus_repository: MundusRepository,
    ) -> None:
        self.evaluator = evaluator
        self.mundus_repository = mundus_repository
        self._projection_cache: dict[str, ExtremeResourceMundusProjection] = {}

    def mundus_projection(self, objective_key: str) -> ExtremeResourceMundusProjection | None:
        key = str(objective_key or "").strip().casefold()
        if key not in ExtremeResourceMundusProjectionService.SUPPORTED_OBJECTIVES:
            return None
        cached = self._projection_cache.get(key)
        if cached is None:
            cached = ExtremeResourceMundusProjectionService(self.mundus_repository).build(key)
            self._projection_cache[key] = cached
        return cached

    def _all_mundus_choices(self) -> tuple[str, ...]:
        values: list[str] = [""]
        seen = {""}
        for raw in self.mundus_repository.list_names():
            name = str(raw or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            values.append(name)
        return tuple(values)

    def mundus_choices(self, objective_key: str | None = None) -> tuple[str, ...]:
        key = str(objective_key or "").strip().casefold()
        if key:
            projection = self.mundus_projection(key)
            if projection is not None and projection.projection_complete:
                return (str(projection.witness),)
        return self._all_mundus_choices()

    def __call__(
        self,
        objective_key: str,
        candidate: ExtremeStructuralCandidate,
    ) -> tuple[float, dict[str, Any], tuple[str, ...]]:
        return self.evaluate_candidate(objective_key, candidate)

    def evaluate_candidate(
        self,
        objective_key: str,
        candidate: ExtremeStructuralCandidate,
        *,
        food: str = "",
        potion: str = "",
        active_buffs: tuple[str, ...] = (),
    ) -> tuple[float, dict[str, Any], tuple[str, ...]]:
        """Pick best retained Mundus while preserving optional outer selections."""
        best_value: float | None = None
        best_payload: dict[str, Any] | None = None
        best_unresolved: tuple[str, ...] = ()
        best_mundus = ""

        for mundus in self.mundus_choices(objective_key):
            kwargs: dict[str, Any] = {"mundus": mundus}
            if str(food or "").strip():
                kwargs["food"] = food
            if str(potion or "").strip():
                kwargs["potion"] = potion
            if tuple(active_buffs or ()):
                kwargs["active_buffs"] = tuple(active_buffs)
            value, payload, unresolved = self.evaluator.evaluate_candidate(
                objective_key,
                candidate,
                **kwargs,
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
        choices = self.mundus_evaluator.mundus_choices(key)
        projection = self.mundus_evaluator.mundus_projection(key)
        searched = tuple((*result.structural_scope, _MUNDUS_SCOPE))
        omitted = tuple(
            axis for axis in result.deferred_dynamic_axes if axis != _MUNDUS_DEFERRED_AXIS
        )
        expanded_count = int(result.candidates_scored) * len(choices)
        denominator_proven = bool(
            result.structural_denominator_proven
            and choices
            and not omitted
            and (projection is None or projection.projection_complete)
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
                            *((projection.unresolved if projection is not None else ())),
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
        mundus_text = (
            f"reviewed {projection.stones_reviewed:,} canonical Mundus stones and retained exact witness {projection.witness}"
            if projection is not None and projection.projection_complete
            else f"searched {len(choices):,} Mundus states including no-Mundus"
        )
        explanation = (
            f"Exhaustively searched the structural denominator and {mundus_text}.",
            f"Evaluated {expanded_count:,} structural/Mundus combinations.",
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
