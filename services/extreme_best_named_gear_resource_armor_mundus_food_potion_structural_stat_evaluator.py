from __future__ import annotations

"""Choose the best named gear + resource armor beneath finite axes.

A reviewed static jewelry-resource trait state may be injected into the factory and
is then materialized inside each canonical gear+armor scorer. The outer search does
not multiply by jewelry because the static jewelry reducer already proves one
strongest continuation witness per max-resource objective.

The resource active-bar evidence service is shared across every gear/armor scorer
created by one factory so canonical skill inventory and proof-reduced route bars
are cached once rather than rediscovered under every equipment witness.

For max-resource records, the Emperor passive has a monotonic Home Keep table.
The global maximum therefore needs only the legal six-Home-Keep active-Emperor
witness. The fixed snapshot marker is consumed by ``CombatState`` and projected
through the shared ``EmperorPassiveInputResolver``; no Emperor math lives here.
"""

from collections.abc import Callable
from typing import Any, Protocol

from minmax.combat_state import EMPEROR_STATE_MARKER_PREFIX
from minmax.mundus_repository import MundusRepository
from minmax.potion_availability_repository import PotionAvailabilityRepository
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from services.extreme_armor_resource_weight_trait_glyph_state_service import (
    ExtremeArmorResourceWeightTraitGlyphState,
    ExtremeArmorResourceWeightTraitGlyphStateCatalog,
)
from services.extreme_jewelry_resource_static_trait_state_service import (
    ExtremeJewelryResourceStaticTraitState,
)
from services.extreme_named_gear_canonical_stat_evaluator import (
    ExtremeNamedGearCanonicalStatEvaluator,
)
from services.extreme_named_gear_resource_armor_canonical_stat_evaluator import (
    ExtremeNamedGearResourceArmorCanonicalStatEvaluator,
)
from services.extreme_named_gear_set_realization_service import ExtremeNamedGearSetRealization
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationResult,
)
from services.extreme_resource_active_bar_state_service import (
    ExtremeResourceActiveBarStateService,
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


_EXTREME_EMPEROR_HOME_KEEPS = 6
_EXTREME_EMPEROR_STATE_MARKER = (
    f"{EMPEROR_STATE_MARKER_PREFIX}{_EXTREME_EMPEROR_HOME_KEEPS}",
)


class _FiniteAxisScorer(Protocol):
    def __call__(
        self,
        objective_key: str,
        candidate: ExtremeStructuralCandidate,
    ) -> tuple[float, dict[str, Any], tuple[str, ...]]: ...


GearResourceArmorEvaluatorFactory = Callable[
    [ExtremeNamedGearSetRealization, ExtremeArmorResourceWeightTraitGlyphState],
    _FiniteAxisScorer,
]


class ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory:
    """Build Mundus/food/potion around one named-gear + resource-armor pair."""

    def __init__(
        self,
        *,
        canonical_evaluator: ExtremeCanonicalStructuralStatEvaluator,
        mundus_repository: MundusRepository,
        provisioning_repository: ProvisioningStaticRepository,
        potion_repository: PotionAvailabilityRepository,
        jewelry_state: ExtremeJewelryResourceStaticTraitState | None = None,
        active_bar_state_service: ExtremeResourceActiveBarStateService | None = None,
    ) -> None:
        self.canonical_evaluator = canonical_evaluator
        self.mundus_repository = mundus_repository
        self.provisioning_repository = provisioning_repository
        self.potion_repository = potion_repository
        self.jewelry_state = jewelry_state

        if active_bar_state_service is None:
            database_path = getattr(canonical_evaluator.optimizer, "database_path", None)
            if database_path is not None:
                active_bar_state_service = ExtremeResourceActiveBarStateService(database_path)
        self.active_bar_state_service = active_bar_state_service

    def __call__(
        self,
        realization: ExtremeNamedGearSetRealization,
        armor_state: ExtremeArmorResourceWeightTraitGlyphState,
    ) -> ExtremeBestMundusFoodPotionStructuralStatEvaluator:
        gear = ExtremeNamedGearCanonicalStatEvaluator(
            evaluator=self.canonical_evaluator,
            realization=realization,
        )
        armor = ExtremeNamedGearResourceArmorCanonicalStatEvaluator(
            evaluator=gear,
            armor_state=armor_state,
            jewelry_state=self.jewelry_state,
            active_bar_state_service=self.active_bar_state_service,
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
            base_active_buffs=_EXTREME_EMPEROR_STATE_MARKER,
        )


class ExtremeBestNamedGearResourceArmorMundusFoodPotionStructuralStatEvaluator:
    """Score every named-gear × combined resource-armor state per structural candidate."""

    def __init__(
        self,
        *,
        gear_realization: ExtremeObjectiveNamedGearSetCatalogRealizationResult,
        armor_catalog: ExtremeArmorResourceWeightTraitGlyphStateCatalog,
        evaluator_factory: GearResourceArmorEvaluatorFactory,
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
    def _armor_identity(state: ExtremeArmorResourceWeightTraitGlyphState) -> tuple[Any, ...]:
        return tuple(state.identity)

    def gear_realizations(self) -> tuple[ExtremeNamedGearSetRealization, ...]:
        unique: dict[tuple[Any, ...], ExtremeNamedGearSetRealization] = {}
        for topology in self.gear_realization.realization.topologies:
            for realization in topology.realizations:
                unique.setdefault(self._gear_identity(realization), realization)
        return tuple(unique[key] for key in sorted(unique))

    def armor_states(self) -> tuple[ExtremeArmorResourceWeightTraitGlyphState, ...]:
        return tuple(sorted(self.armor_catalog.states, key=self._armor_identity))

    @property
    def unresolved(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*self.gear_realization.unresolved, *self.armor_catalog.unresolved)))

    @property
    def gear_denominator_proven(self) -> bool:
        return bool(self.gear_realization.denominator_proven)

    @property
    def reviewed_resource_armor_denominator_proven(self) -> bool:
        return bool(self.armor_catalog.denominator_proven)

    def _evaluator_for(
        self,
        realization: ExtremeNamedGearSetRealization,
        armor_state: ExtremeArmorResourceWeightTraitGlyphState,
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
                "Extreme resource armor catalog objective mismatch: "
                f"catalog={self.armor_catalog.objective_key!r}, requested={key!r}"
            )

        gear_rows = self.gear_realizations()
        armor_rows = self.armor_states()
        if not gear_rows:
            raise ValueError("Extreme named gear search produced no physically realized gear candidate")
        if not armor_rows:
            raise ValueError("Extreme resource armor search produced no combined weight/trait/glyph state")

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
            raise ValueError("Extreme named gear + resource armor search produced no scored candidate")

        trait_glyph = self.armor_catalog.trait_glyph_catalog
        weight = self.armor_catalog.weight_catalog
        best_payload["gear_candidates_scored"] = len(gear_rows)
        best_payload["resource_armor_states_scored"] = len(armor_rows)
        best_payload["gear_resource_armor_candidates_scored"] = len(gear_rows) * len(armor_rows)
        best_payload["gear_denominator_proven"] = self.gear_denominator_proven
        best_payload["reviewed_resource_armor_denominator_proven"] = (
            self.reviewed_resource_armor_denominator_proven
        )
        best_payload["armor_weight_states_reviewed"] = len(weight.states)
        best_payload["armor_weight_raw_loadouts_reviewed"] = weight.raw_loadouts_reviewed
        best_payload["armor_weight_dominated_loadouts_pruned"] = weight.dominated_loadouts_pruned
        best_payload["armor_glyph_choices_reviewed"] = trait_glyph.glyph_choices_reviewed
        best_payload["armor_trait_glyph_dominated_states_pruned"] = trait_glyph.dominated_states_pruned
        best_payload["emperor_state"] = {
            "is_emperor": True,
            "in_home_campaign": True,
            "home_keeps": _EXTREME_EMPEROR_HOME_KEEPS,
            "max_resource_percent": 0.75,
        }
        return best_value, best_payload, tuple(dict.fromkeys(unresolved))
