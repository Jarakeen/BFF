from __future__ import annotations

"""Choose the best proven named gear witness beneath the finite consumable axes.

For one structural candidate this layer evaluates every objective-surviving named
gear realization. Each gear witness is materialized below the existing
Mundus -> food -> potion search and is scored through the canonical Extreme stat
pipeline. No set bonus is added numerically here.

The objective-aware gear realization result remains the denominator authority.
If that result is truncated or unresolved, this scorer may still return a useful
lower-bound winner, but it cannot claim gear-denominator proof.
"""

from collections.abc import Callable
from typing import Any, Protocol

from minmax.mundus_repository import MundusRepository
from minmax.potion_availability_repository import PotionAvailabilityRepository
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from services.extreme_named_gear_canonical_stat_evaluator import (
    ExtremeNamedGearCanonicalStatEvaluator,
)
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationResult,
)
from services.extreme_structural_core_stat_record_service import (
    ExtremeCanonicalStructuralStatEvaluator,
)
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate
from services.extreme_structural_mundus_core_stat_record_service import (
    ExtremeBestMundusStructuralStatEvaluator,
)
from services.extreme_structural_mundus_food_core_stat_record_service import (
    ExtremeBestMundusFoodStructuralStatEvaluator,
)
from services.extreme_structural_mundus_food_potion_core_stat_record_service import (
    ExtremeBestMundusFoodPotionStructuralStatEvaluator,
)
from services.extreme_twice_born_mundus_structural_stat_evaluator import (
    ExtremeTwiceBornMundusStructuralStatEvaluator,
)


class _FiniteAxisScorer(Protocol):
    def __call__(
        self,
        objective_key: str,
        candidate: ExtremeStructuralCandidate,
    ) -> tuple[float, dict[str, Any], tuple[str, ...]]: ...


GearEvaluatorFactory = Callable[[ExtremeNamedGearSetRealization], _FiniteAxisScorer]


class ExtremeNamedGearFiniteAxisEvaluatorFactory:
    """Build the established Mundus/food/potion stack around one gear witness."""

    _TWICE_BORN_STAR = "Twice-Born Star"

    def __init__(
        self,
        *,
        canonical_evaluator: ExtremeCanonicalStructuralStatEvaluator,
        mundus_repository: MundusRepository,
        provisioning_repository: ProvisioningStaticRepository,
        potion_repository: PotionAvailabilityRepository,
    ) -> None:
        self.canonical_evaluator = canonical_evaluator
        self.mundus_repository = mundus_repository
        self.provisioning_repository = provisioning_repository
        self.potion_repository = potion_repository

    @classmethod
    def _has_active_twice_born_star(
        cls,
        realization: ExtremeNamedGearSetRealization,
    ) -> bool:
        return any(
            str(name) == cls._TWICE_BORN_STAR and int(count) >= 5
            for name, count in zip(realization.set_names, realization.counts)
        )

    def __call__(
        self,
        realization: ExtremeNamedGearSetRealization,
    ) -> ExtremeBestMundusFoodPotionStructuralStatEvaluator:
        gear = ExtremeNamedGearCanonicalStatEvaluator(
            evaluator=self.canonical_evaluator,
            realization=realization,
        )
        if self._has_active_twice_born_star(realization):
            mundus = ExtremeTwiceBornMundusStructuralStatEvaluator(
                evaluator=gear,
                mundus_repository=self.mundus_repository,
            )
        else:
            mundus = ExtremeBestMundusStructuralStatEvaluator(
                evaluator=gear,
                mundus_repository=self.mundus_repository,
            )
        food = ExtremeBestMundusFoodStructuralStatEvaluator(
            mundus_evaluator=mundus,
            provisioning_repository=self.provisioning_repository,
        )
        return ExtremeBestMundusFoodPotionStructuralStatEvaluator(
            food_evaluator=food,
            potion_repository=self.potion_repository,
        )


class ExtremeBestNamedGearMundusFoodPotionStructuralStatEvaluator:
    """Score every legal named gear witness for one structural candidate."""

    def __init__(
        self,
        *,
        gear_realization: ExtremeObjectiveNamedGearSetCatalogRealizationResult,
        evaluator_factory: GearEvaluatorFactory,
    ) -> None:
        self.gear_realization = gear_realization
        self.evaluator_factory = evaluator_factory
        self._evaluators: dict[tuple[Any, ...], _FiniteAxisScorer] = {}

    @staticmethod
    def _identity(realization: ExtremeNamedGearSetRealization) -> tuple[Any, ...]:
        return (
            tuple(realization.set_ids),
            tuple(realization.counts),
            realization.weapon_shape.value,
            tuple(
                (row.slot, row.set_id, row.weapon_type)
                for row in realization.assignments
            ),
        )

    def gear_realizations(self) -> tuple[ExtremeNamedGearSetRealization, ...]:
        unique: dict[tuple[Any, ...], ExtremeNamedGearSetRealization] = {}
        for topology in self.gear_realization.realization.topologies:
            for realization in topology.realizations:
                unique.setdefault(self._identity(realization), realization)
        return tuple(unique[key] for key in sorted(unique))

    @property
    def unresolved(self) -> tuple[str, ...]:
        return tuple(self.gear_realization.unresolved)

    @property
    def gear_denominator_proven(self) -> bool:
        return bool(self.gear_realization.denominator_proven)

    def _evaluator_for(self, realization: ExtremeNamedGearSetRealization) -> _FiniteAxisScorer:
        identity = self._identity(realization)
        evaluator = self._evaluators.get(identity)
        if evaluator is None:
            evaluator = self.evaluator_factory(realization)
            self._evaluators[identity] = evaluator
        return evaluator

    def __call__(
        self,
        objective_key: str,
        candidate: ExtremeStructuralCandidate,
    ) -> tuple[float, dict[str, Any], tuple[str, ...]]:
        realizations = self.gear_realizations()
        if not realizations:
            raise ValueError(
                "Extreme named gear search produced no physically realized gear candidate"
            )

        best_value: float | None = None
        best_payload: dict[str, Any] | None = None
        best_identity: tuple[Any, ...] | None = None
        unresolved: list[str] = list(self.unresolved)

        for realization in realizations:
            evaluator = self._evaluator_for(realization)
            value, payload, candidate_unresolved = evaluator(objective_key, candidate)
            unresolved.extend(str(item) for item in candidate_unresolved if str(item))
            score = float(value)
            identity = self._identity(realization)
            if (
                best_value is None
                or score > best_value + 1e-9
                or (
                    abs(score - best_value) <= 1e-9
                    and (best_identity is None or identity < best_identity)
                )
            ):
                best_value = score
                best_payload = dict(payload)
                best_identity = identity

        if best_value is None or best_payload is None:
            raise ValueError("Extreme named gear search produced no scored candidate")

        best_payload["gear_candidates_scored"] = len(realizations)
        best_payload["gear_assignments_considered"] = int(
            self.gear_realization.assignments_considered
        )
        best_payload["gear_assignments_realized"] = int(
            self.gear_realization.assignments_realized
        )
        best_payload["gear_assignments_rejected"] = int(
            self.gear_realization.assignments_rejected
        )
        best_payload["gear_breakpoints_pruned_irrelevant"] = int(
            self.gear_realization.breakpoints_pruned_irrelevant
        )
        best_payload["gear_denominator_proven"] = self.gear_denominator_proven
        return best_value, best_payload, tuple(dict.fromkeys(unresolved))
