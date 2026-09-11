from __future__ import annotations

"""Add canonical potion-active snapshots to structural + Mundus + food search.

Potion selection and potion activation are deliberately separate.  The canonical
PotionAvailabilityRepository proves which U50 formulas/traits are available.
Only source-backed traits with an existing named-buff mapping are projected into
an explicit CombatState for the scored snapshot.  No selected potion is silently
assumed active by the lower calculation layers.

Callers may additionally supply fixed transient-state markers that apply to every
potion state. This lets higher finite-axis searches compose an explicitly reviewed
runtime condition, such as the Extreme Emperor ceiling, without duplicating the
potion search or stat math.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from minmax.alchemy_potion_buff_semantics import potion_buff_for_trait
from minmax.combat_effect_semantics import GameUpdate
from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from minmax.potion_availability_repository import PotionAvailabilityRepository
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
from services.extreme_structural_mundus_food_core_stat_record_service import (
    ExtremeBestMundusFoodStructuralStatEvaluator,
    _FOOD_DEFERRED_AXIS,
    _FOOD_SCOPE,
)


_POTION_DEFERRED_AXIS = "potions"
_POTION_SCOPE = "all canonical Update-50 alchemy potion formulas plus no-potion baseline"


@dataclass(frozen=True)
class ExtremePotionSnapshotState:
    selection: str
    active_buffs: tuple[str, ...] = ()


class ExtremeBestMundusFoodPotionStructuralStatEvaluator:
    """Score every canonical potion formula over the nested food/Mundus search."""

    def __init__(
        self,
        *,
        food_evaluator: ExtremeBestMundusFoodStructuralStatEvaluator,
        potion_repository: PotionAvailabilityRepository,
        base_active_buffs: tuple[str, ...] = (),
    ) -> None:
        self.food_evaluator = food_evaluator
        self.potion_repository = potion_repository
        self.base_active_buffs = tuple(
            dict.fromkeys(
                str(value or "").strip()
                for value in base_active_buffs
                if str(value or "").strip()
            )
        )
        self._states_cache: tuple[ExtremePotionSnapshotState, ...] | None = None
        self._unresolved_cache: tuple[str, ...] | None = None
        self._denominator_proven_cache: bool | None = None

    def potion_states(self) -> tuple[ExtremePotionSnapshotState, ...]:
        if self._states_cache is not None:
            return self._states_cache

        catalog = self.potion_repository.catalog()
        states: list[ExtremePotionSnapshotState] = [ExtremePotionSnapshotState(selection="")]
        unresolved: list[str] = [str(item) for item in catalog.unresolved if item]
        seen = {""}

        for formula in catalog.formulas:
            selection = str(formula.canonical_id or "").strip()
            if not selection or selection in seen:
                continue
            seen.add(selection)
            availability = self.potion_repository.resolve(selection)
            unresolved.extend(str(item) for item in availability.unresolved if item)

            buffs: list[str] = []
            for trait in availability.canonical_traits:
                named_buff = potion_buff_for_trait(trait, game_update=GameUpdate.U50)
                if named_buff and named_buff not in buffs:
                    buffs.append(named_buff)
            states.append(
                ExtremePotionSnapshotState(
                    selection=selection,
                    active_buffs=tuple(buffs),
                )
            )

        self._states_cache = tuple(states)
        self._unresolved_cache = tuple(dict.fromkeys(unresolved))
        self._denominator_proven_cache = bool(catalog.formulas) and not self._unresolved_cache
        return self._states_cache

    @property
    def unresolved(self) -> tuple[str, ...]:
        self.potion_states()
        return tuple(self._unresolved_cache or ())

    @property
    def denominator_proven(self) -> bool:
        self.potion_states()
        return bool(self._denominator_proven_cache)

    def __call__(
        self,
        objective_key: str,
        candidate: ExtremeStructuralCandidate,
    ) -> tuple[float, dict[str, Any], tuple[str, ...]]:
        best_value: float | None = None
        best_payload: dict[str, Any] | None = None
        best_selection = ""
        unresolved: list[str] = list(self.unresolved)

        for state in self.potion_states():
            snapshot_buffs = tuple(
                dict.fromkeys((*self.base_active_buffs, *state.active_buffs))
            )
            value, payload, candidate_unresolved = self.food_evaluator.evaluate_candidate(
                objective_key,
                candidate,
                potion=state.selection,
                active_buffs=snapshot_buffs,
            )
            unresolved.extend(str(item) for item in candidate_unresolved if item)
            score = float(value)
            if (
                best_value is None
                or score > best_value + 1e-9
                or (
                    abs(score - best_value) <= 1e-9
                    and state.selection.casefold() < best_selection.casefold()
                )
            ):
                best_value = score
                best_payload = payload
                best_selection = state.selection

        if best_value is None or best_payload is None:
            raise ValueError("Extreme potion search produced no legal potion state")
        return best_value, best_payload, tuple(dict.fromkeys(unresolved))


class ExtremeStructuralMundusFoodPotionCoreStatRecordService:
    """Return structural + Mundus + food + potion lower bounds for core records."""

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        optimizer: ExtremeOptimizationService | None = None,
        search_service: ExtremeStructuralGlobalSearchService[dict[str, Any]] | None = None,
        evaluator: ExtremeBestMundusFoodPotionStructuralStatEvaluator | None = None,
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
            food = ExtremeBestMundusFoodStructuralStatEvaluator(
                mundus_evaluator=mundus,
                provisioning_repository=ProvisioningStaticRepository(resolved_database),
            )
            evaluator = ExtremeBestMundusFoodPotionStructuralStatEvaluator(
                food_evaluator=food,
                potion_repository=PotionAvailabilityRepository(
                    resolved_database,
                    game_update=GameUpdate.U50,
                ),
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
                "Extreme structural+Mundus+food+potion core-stat search does not support "
                f"objective: {objective_key!r}"
            )

        result: ExtremeStructuralGlobalSearchResult[dict[str, Any]] = self.search_service.search(key)
        potion_states = self.evaluator.potion_states()
        food_choices = self.evaluator.food_evaluator.food_choices()
        mundus_choices = self.evaluator.food_evaluator.mundus_evaluator.mundus_choices()
        searched = tuple((*result.structural_scope, _MUNDUS_SCOPE, _FOOD_SCOPE, _POTION_SCOPE))
        omitted = tuple(
            axis
            for axis in result.deferred_dynamic_axes
            if axis not in {_MUNDUS_DEFERRED_AXIS, _FOOD_DEFERRED_AXIS, _POTION_DEFERRED_AXIS}
        )
        expanded_count = (
            int(result.candidates_scored)
            * len(mundus_choices)
            * len(food_choices)
            * len(potion_states)
        )
        denominator_proven = bool(
            result.structural_denominator_proven
            and mundus_choices
            and food_choices
            and potion_states
            and self.evaluator.denominator_proven
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
                            "Structural + Mundus + food + potion Extreme search produced no scored candidate",
                            *self.evaluator.unresolved,
                            *result.unresolved,
                        )
                    )
                ),
                search_coverage=coverage,
            )

        winner = result.best
        winner_mundus = ""
        winner_food = ""
        winner_potion = ""
        winner_buffs: tuple[str, ...] = ()
        if isinstance(winner.payload, dict):
            winner_mundus = str(winner.payload.get("mundus") or "")
            winner_food = str(winner.payload.get("food") or "")
            winner_potion = str(winner.payload.get("potion") or "")
            winner_buffs = tuple(winner.payload.get("active_buffs") or ())

        runtime_prerequisites = ()
        if winner_potion:
            runtime_prerequisites = (
                "Winning potion formula must be activated and its mapped effects active at the scored snapshot.",
            )

        explanation = (
            "Exhaustively searched structural candidates × every Update-50 Mundus × canonical food/drink × canonical potion formula state.",
            f"Evaluated {expanded_count:,} combinations across {len(mundus_choices):,} Mundus, {len(food_choices):,} food, and {len(potion_states):,} potion states including empty baselines.",
            f"Winning Mundus: {winner_mundus or 'none'}; food/drink: {winner_food or 'none'}; potion: {winner_potion or 'none'}.",
            "Potion selection proves availability; named potion buffs are applied only in the explicit active snapshot scored by this layer.",
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
            runtime_prerequisites=runtime_prerequisites,
            self_provided_conditions=tuple(winner_buffs),
            unresolved=tuple(result.unresolved),
            search_coverage=coverage,
            explanation=explanation,
        )
