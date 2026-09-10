from __future__ import annotations

"""Choose the best named-gear + reviewed armor state beneath finite consumable axes.

For one structural candidate this layer evaluates every objective-surviving named
gear realization crossed with every reviewed seven-piece armor weight/static-trait
state.  Each combination is materialized into a real ``PlayerBuild`` beneath the
existing Mundus -> food -> potion search and scored through the canonical Extreme
stat pipeline.

The armor state catalog proves only its reviewed source family.  It does not claim
that glyph-dependent or runtime-only traits are closed.
"""

from collections.abc import Callable
from typing import Any, Protocol

from minmax.mundus_repository import MundusRepository
from minmax.potion_availability_repository import PotionAvailabilityRepository
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from services.extreme_armor_weight_trait_state_service import (
    ExtremeArmorWeightTraitState,
    ExtremeArmorWeightTraitStateCatalog,
)
from services.extreme_named_gear_armor_canonical_stat_evaluator import (
    ExtremeNamedGearArmorCanonicalStatEvaluator,
)
from services.extreme_named_gear_canonical_stat_evaluator import (
    ExtremeNamedGearCanonicalStatEvaluator,
)
from services.extreme_named_gear_set_realization_service import ExtremeNamedGearSetRealization
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationResult,
)
from services.extreme_structural_core_stat_record_service import ExtremeCanonicalStructuralStatEvaluator
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate
from services.extreme_structural_mundus_core_stat_record_service import ExtremeBestMundusStructuralStatEvaluator
from services.extreme_structural_mundus_food_core_stat_record_service import (
    ExtremeBestMundusFoodStructuralStatEvaluator,
)
from services.extreme_structural_mundus_food_potion_core_stat_record_service import (
    ExtremeBestMundusFoodPotionStructuralStatEvaluator,
)


class _FiniteAxisScorer(Protocol):
    def __call__(
        self,
        objective_key: str,
        candidate: ExtremeStructuralCandidate,
    ) -> tuple[float, dict[str, Any], tuple[str, ...]]: ...


GearArmorEvaluatorFactory = Callable[
    [ExtremeNamedGearSetRealization, ExtremeArmorWeightTraitState],
    _FiniteAxisScorer,
]


class ExtremeNamedGearArmorFiniteAxisEvaluatorFactory:
    """Build Mundus/food/potion around one named-gear + armor-state pair."""

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

    def __call__(
        self,
        realization: ExtremeNamedGearSetRealization,
        armor_state: ExtremeArmorWeightTraitState,
    ) -> ExtremeBestMundusFoodPotionStructuralStatEvaluator:
        gear = ExtremeNamedGearCanonicalStatEvaluator(
            evaluator=self.canonical_evaluator,
            realization=realization,
        )
        armor = ExtremeNamedGearArmorCanonicalStatEvaluator(
            evaluator=gear,
            armor_state=armor_state,
        )
        mundus = ExtremeBestMundusStructuralStatEvaluator(
            evaluator=armor,
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


class ExtremeBestNamedGearArmorMundusFoodPotionStructuralStatEvaluator:
    """Score every named-gear × reviewed-armor state for one structural candidate."""

    def __init__(
        self,
        *,
        gear_realization: ExtremeObjectiveNamedGearSetCatalogRealizationResult,
        armor_catalog: ExtremeArmorWeightTraitStateCatalog,
        evaluator_factory: GearArmorEvaluatorFactory,
    ) -> None:
        self.gear_realization = gear_realization
        self.armor_catalog = armor_catalog
        self.evaluator_factory = evaluator_factory
        self._evaluators: dict[tuple[Any, ...], _FiniteAxisScorer] = {}

    @staticmethod
    def _gear_identity(realization: ExtremeNamedGearSetRealization) -> tuple[Any, ...]:
        return (
            tuple(realization.set_ids),
            tuple(realization.counts),
            realization.weapon_shape.value,
            tuple((row.slot, row.set_id, row.weapon_type) for row in realization.assignments),
        )

    @staticmethod
    def _armor_identity(state: ExtremeArmorWeightTraitState) -> tuple[Any, ...]:
        return tuple(state.identity)

    def gear_realizations(self) -> tuple[ExtremeNamedGearSetRealization, ...]:
        unique: dict[tuple[Any, ...], ExtremeNamedGearSetRealization] = {}
        for topology in self.gear_realization.realization.topologies:
            for realization in topology.realizations:
                unique.setdefault(self._gear_identity(realization), realization)
        return tuple(unique[key] for key in sorted(unique))

    def armor_states(self) -> tuple[ExtremeArmorWeightTraitState, ...]:
        return tuple(sorted(self.armor_catalog.states, key=self._armor_identity))

    @property
    def unresolved(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                (*self.gear_realization.unresolved, *self.armor_catalog.unresolved)
            )
        )

    @property
    def gear_denominator_proven(self) -> bool:
        return bool(self.gear_realization.denominator_proven)

    @property
    def reviewed_armor_denominator_proven(self) -> bool:
        return bool(self.armor_catalog.reviewed_source_denominator_proven)

    def _evaluator_for(
        self,
        realization: ExtremeNamedGearSetRealization,
        armor_state: ExtremeArmorWeightTraitState,
    ) -> _FiniteAxisScorer:
        identity = (self._gear_identity(realization), self._armor_identity(armor_state))
        evaluator = self._evaluators.get(identity)
        if evaluator is None:
            evaluator = self.evaluator_factory(realization, armor_state)
            self._evaluators[identity] = evaluator
        return evaluator

    def __call__(
        self,
        objective_key: str,
        candidate: ExtremeStructuralCandidate,
    ) -> tuple[float, dict[str, Any], tuple[str, ...]]:
        key = str(objective_key or "").strip().casefold()
        if key != self.armor_catalog.objective_key:
            raise ValueError(
                "Extreme armor catalog objective mismatch: "
                f"catalog={self.armor_catalog.objective_key!r}, requested={key!r}"
            )

        gear_rows = self.gear_realizations()
        armor_rows = self.armor_states()
        if not gear_rows:
            raise ValueError("Extreme named gear search produced no physically realized gear candidate")
        if not armor_rows:
            raise ValueError("Extreme reviewed armor search produced no armor state")

        best_value: float | None = None
        best_payload: dict[str, Any] | None = None
        best_identity: tuple[Any, ...] | None = None
        unresolved: list[str] = list(self.unresolved)

        for realization in gear_rows:
            gear_identity = self._gear_identity(realization)
            for armor_state in armor_rows:
                evaluator = self._evaluator_for(realization, armor_state)
                value, payload, candidate_unresolved = evaluator(key, candidate)
                unresolved.extend(str(item) for item in candidate_unresolved if str(item))
                score = float(value)
                identity = (gear_identity, self._armor_identity(armor_state))
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
            raise ValueError("Extreme named gear + armor search produced no scored candidate")

        best_payload["gear_candidates_scored"] = len(gear_rows)
        best_payload["armor_states_scored"] = len(armor_rows)
        best_payload["gear_armor_candidates_scored"] = len(gear_rows) * len(armor_rows)
        best_payload["gear_denominator_proven"] = self.gear_denominator_proven
        best_payload["reviewed_armor_denominator_proven"] = self.reviewed_armor_denominator_proven
        best_payload["armor_reviewed_traits"] = tuple(self.armor_catalog.reviewed_traits)
        return best_value, best_payload, tuple(dict.fromkeys(unresolved))
