from __future__ import annotations

"""Add the finite food/drink axis to structural + Mundus Extreme stat search."""

from pathlib import Path
from typing import Any

from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from minmax.provisioning_static_repository import ProvisioningStaticRepository
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
from services.extreme_structural_mundus_core_stat_record_service import (
    ExtremeBestMundusStructuralStatEvaluator,
    _MUNDUS_DEFERRED_AXIS,
    _MUNDUS_SCOPE,
)


_FOOD_DEFERRED_AXIS = "food/drink"
_FOOD_SCOPE = "all canonical food/drink choices present in eso.db plus no-food baseline"


class ExtremeBestMundusFoodStructuralStatEvaluator:
    """Score every canonical food choice, with exhaustive Mundus choice nested inside."""

    def __init__(
        self,
        *,
        mundus_evaluator: ExtremeBestMundusStructuralStatEvaluator,
        provisioning_repository: ProvisioningStaticRepository,
    ) -> None:
        self.mundus_evaluator = mundus_evaluator
        self.provisioning_repository = provisioning_repository

    def food_choices(self) -> tuple[str, ...]:
        values: list[str] = [""]
        seen = {""}
        for raw in self.provisioning_repository.list_names():
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
        return self.evaluate_candidate(objective_key, candidate)

    def evaluate_candidate(
        self,
        objective_key: str,
        candidate: ExtremeStructuralCandidate,
        *,
        potion: str = "",
        active_buffs: tuple[str, ...] = (),
    ) -> tuple[float, dict[str, Any], tuple[str, ...]]:
        """Pick best food while preserving an optional outer potion-active state."""
        best_value: float | None = None
        best_payload: dict[str, Any] | None = None
        best_food = ""
        unresolved_across_foods: list[str] = []

        for food in self.food_choices():
            if food:
                _, food_unresolved = self.provisioning_repository.resolve(food)
                unresolved_across_foods.extend(str(item) for item in food_unresolved if item)

            kwargs: dict[str, Any] = {"food": food}
            if str(potion or "").strip():
                kwargs["potion"] = potion
            if tuple(active_buffs or ()):
                kwargs["active_buffs"] = tuple(active_buffs)
            value, payload, unresolved = self.mundus_evaluator.evaluate_candidate(
                objective_key,
                candidate,
                **kwargs,
            )
            unresolved_across_foods.extend(str(item) for item in unresolved if item)
            score = float(value)
            if (
                best_value is None
                or score > best_value + 1e-9
                or (
                    abs(score - best_value) <= 1e-9
                    and food.casefold() < best_food.casefold()
                )
            ):
                best_value = score
                best_payload = payload
                best_food = food

        if best_value is None or best_payload is None:
            raise ValueError("Extreme food/drink search produced no legal candidate")

        return (
            best_value,
            best_payload,
            tuple(dict.fromkeys(unresolved_across_foods)),
        )


class ExtremeStructuralMundusFoodCoreStatRecordService:
    """Return structural + Mundus + food lower bounds for executable core records."""

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        optimizer: ExtremeOptimizationService | None = None,
        search_service: ExtremeStructuralGlobalSearchService[dict[str, Any]] | None = None,
        evaluator: ExtremeBestMundusFoodStructuralStatEvaluator | None = None,
    ) -> None:
        self.optimizer = optimizer or ExtremeOptimizationService(database_path=database_path)
        resolved_database = Path(database_path or self.optimizer.database_path)

        if evaluator is None:
            canonical = ExtremeCanonicalStructuralStatEvaluator(
                optimizer=self.optimizer,
                progression_service=ExtremeHypotheticalClassProgressionService(resolved_database),
            )
            mundus = ExtremeBestMundusStructuralStatEvaluator(
                evaluator=canonical,
                mundus_repository=MundusRepository(
                    resolved_database,
                    game_update=U50_GAME_UPDATE,
                    initialize=False,
                ),
            )
            evaluator = ExtremeBestMundusFoodStructuralStatEvaluator(
                mundus_evaluator=mundus,
                provisioning_repository=ProvisioningStaticRepository(resolved_database),
            )
        self.evaluator = evaluator

        self.search_service = search_service or ExtremeStructuralGlobalSearchService(
            ExtremeGlobalSearchUniverseService(resolved_database),
            scorer=self.evaluator,
        )

    def record(self, objective_key: str) -> ExtremeRecordResult:
        key = str(objective_key or "").strip().casefold()
        if not ExtremeCoreStatRecordService.supports(key):
            raise ValueError(
                f"Extreme structural+Mundus+food core-stat search does not support objective: {objective_key!r}"
            )

        result: ExtremeStructuralGlobalSearchResult[dict[str, Any]] = self.search_service.search(key)
        food_choices = self.evaluator.food_choices()
        mundus_choices = self.evaluator.mundus_evaluator.mundus_choices()
        searched = tuple((*result.structural_scope, _MUNDUS_SCOPE, _FOOD_SCOPE))
        omitted = tuple(
            axis
            for axis in result.deferred_dynamic_axes
            if axis not in {_MUNDUS_DEFERRED_AXIS, _FOOD_DEFERRED_AXIS}
        )
        expanded_count = int(result.candidates_scored) * len(mundus_choices) * len(food_choices)
        denominator_proven = bool(
            result.structural_denominator_proven
            and mundus_choices
            and food_choices
            and not omitted
            and not result.unresolved
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
                            "Structural + Mundus + food Extreme search produced no scored candidate",
                            *result.unresolved,
                        )
                    )
                ),
                search_coverage=coverage,
            )

        winner = result.best
        winner_food = ""
        winner_mundus = ""
        if isinstance(winner.payload, dict):
            winner_food = str(winner.payload.get("food") or "")
            winner_mundus = str(winner.payload.get("mundus") or "")

        explanation = (
            "Exhaustively searched structural candidates × every Update-50 Mundus choice × every canonical food/drink choice.",
            f"Evaluated {expanded_count:,} structural/Mundus/food combinations across {len(mundus_choices):,} Mundus states and {len(food_choices):,} food states.",
            f"Winning Mundus: {winner_mundus or 'none'}; winning food/drink: {winner_food or 'none'}.",
            "Unmapped legal provisioning entries remain unresolved proof blockers rather than being discarded as numerical losers.",
            "Other dynamic axes remain deferred, so this is not yet a globally proven Extreme Record.",
        )
        return ExtremeRecordResult.for_objective(
            key,
            raw_value=float(winner.value),
            proof_status=(
                ExtremeRecordProofStatus.PROVEN
                if denominator_proven
                else ExtremeRecordProofStatus.LOWER_BOUND
            ),
            winning_build=winner.payload,
            unit=ExtremeStructuralCoreStatRecordService._unit(key),
            unresolved=tuple(result.unresolved),
            search_coverage=coverage,
            explanation=explanation,
        )
