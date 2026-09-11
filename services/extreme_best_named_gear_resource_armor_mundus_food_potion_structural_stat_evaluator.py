from __future__ import annotations

"""Choose the best named gear + resource armor beneath finite axes.

A reviewed static jewelry-resource trait state may be injected into the factory and
is then materialized inside each canonical gear+armor scorer. The outer search does
not multiply by jewelry because the static jewelry reducer already proves one
strongest continuation witness per max-resource objective.

The resource active-bar evidence service is shared across every gear/armor scorer
created by one factory so canonical skill inventory and proof-reduced route bars
are cached once rather than rediscovered under every equipment witness.

Static snapshot objectives score only the active-bar realization, but that snapshot
must now participate in at least one complete legal front/back gear state. This
closes the two-bar legality denominator without multiplying snapshot scoring by
inactive-bar permutations that cannot affect the requested active snapshot.

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
from services.extreme_dual_bar_gear_state_catalog_service import (
    ExtremeDualBarGearStateCatalog,
    ExtremeDualBarGearStateCatalogService,
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
from services.extreme_resource_active_skill_coverage_audit_service import (
    ExtremeResourceActiveSkillCoverageAuditService,
)
from services.extreme_resource_blood_magic_canonical_stat_evaluator import (
    ExtremeResourceBloodMagicCanonicalStatEvaluator,
)
from services.extreme_resource_champion_point_state_service import (
    ExtremeResourceChampionPointStateService,
)
from services.extreme_second_mundus_forwarding_evaluator import (
    ExtremeSecondMundusForwardingEvaluator,
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
from services.extreme_twice_born_mundus_structural_stat_evaluator import (
    ExtremeTwiceBornMundusStructuralStatEvaluator,
)


_EXTREME_EMPEROR_HOME_KEEPS = 6
_EXTREME_EMPEROR_STATE_MARKER = (
    f"{EMPEROR_STATE_MARKER_PREFIX}{_EXTREME_EMPEROR_HOME_KEEPS}",
)
_RESOURCE_CHAMPION_POINT_SCOPE = (
    "all canonical Champion Point stars reviewed for the requested max resource; "
    "resource-relevant non-slottable stars are maxed and the strongest legal up-to-four "
    "resource-relevant slottable stars are materialized into the Champion Bar"
)
_RESOURCE_ACTIVE_SKILL_SCOPE = (
    "all canonical active skills and morphs reviewed for direct max-resource mutation; "
    "none directly modifies the requested max resource, while separate proof-reduced "
    "bar witnesses cover resource-relevant passive slot conditions"
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

    _TWICE_BORN_STAR = "Twice-Born Star"

    def __init__(
        self,
        *,
        canonical_evaluator: ExtremeCanonicalStructuralStatEvaluator,
        mundus_repository: MundusRepository,
        provisioning_repository: ProvisioningStaticRepository,
        potion_repository: PotionAvailabilityRepository,
        jewelry_state: ExtremeJewelryResourceStaticTraitState | None = None,
        active_bar_state_service: ExtremeResourceActiveBarStateService | None = None,
        champion_point_state_service: ExtremeResourceChampionPointStateService | None = None,
        active_skill_coverage_audit_service: ExtremeResourceActiveSkillCoverageAuditService | None = None,
    ) -> None:
        self.canonical_evaluator = canonical_evaluator
        self.mundus_repository = mundus_repository
        self.provisioning_repository = provisioning_repository
        self.potion_repository = potion_repository
        self.jewelry_state = jewelry_state

        database_path = getattr(canonical_evaluator.optimizer, "database_path", None)
        if active_bar_state_service is None and database_path is not None:
            active_bar_state_service = ExtremeResourceActiveBarStateService(database_path)
        self.active_bar_state_service = active_bar_state_service

        if champion_point_state_service is None and database_path is not None:
            champion_point_state_service = ExtremeResourceChampionPointStateService(database_path)
        self.champion_point_state_service = champion_point_state_service

        if active_skill_coverage_audit_service is None and database_path is not None:
            active_skill_coverage_audit_service = ExtremeResourceActiveSkillCoverageAuditService(
                database_path
            )
        self.active_skill_coverage_audit_service = active_skill_coverage_audit_service

    @classmethod
    def _has_active_twice_born_star(
        cls,
        realization: ExtremeNamedGearSetRealization,
    ) -> bool:
        return any(
            str(name) == cls._TWICE_BORN_STAR and int(count) >= 5
            for name, count in zip(realization.set_names, realization.counts)
        )

    def champion_point_state(self, objective_key: str):
        if self.champion_point_state_service is None:
            return None
        return self.champion_point_state_service.build(objective_key)

    def active_skill_audit(self, objective_key: str):
        if self.active_skill_coverage_audit_service is None:
            return None
        return self.active_skill_coverage_audit_service.build(objective_key)

    def __call__(
        self,
        realization: ExtremeNamedGearSetRealization,
        armor_state: ExtremeArmorResourceWeightTraitGlyphState,
    ) -> ExtremeBestMundusFoodPotionStructuralStatEvaluator:
        gear = ExtremeNamedGearCanonicalStatEvaluator(
            evaluator=self.canonical_evaluator,
            realization=realization,
        )
        twice_born = self._has_active_twice_born_star(realization)
        second_mundus_forwarder = (
            ExtremeSecondMundusForwardingEvaluator(gear)
            if twice_born
            else None
        )
        armor = ExtremeNamedGearResourceArmorCanonicalStatEvaluator(
            evaluator=second_mundus_forwarder or gear,
            armor_state=armor_state,
            jewelry_state=self.jewelry_state,
            active_bar_state_service=self.active_bar_state_service,
            champion_point_state_service=self.champion_point_state_service,
        )
        if self.active_bar_state_service is not None:
            armor = ExtremeResourceBloodMagicCanonicalStatEvaluator(
                evaluator=armor,
                active_bar_state_service=self.active_bar_state_service,
                database_path=getattr(self.canonical_evaluator.optimizer, "database_path", None),
            )
        if twice_born and second_mundus_forwarder is not None:
            mundus = ExtremeTwiceBornMundusStructuralStatEvaluator(
                evaluator=armor,
                mundus_repository=self.mundus_repository,
                second_mundus_setter=second_mundus_forwarder.set_second_mundus,
            )
        else:
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
    """Score every dual-bar-admissible named-gear × resource-armor state."""

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
        self._dual_bar_catalog: ExtremeDualBarGearStateCatalog | None = None

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

    def _raw_gear_realizations(self) -> tuple[ExtremeNamedGearSetRealization, ...]:
        unique: dict[tuple[Any, ...], ExtremeNamedGearSetRealization] = {}
        for topology in self.gear_realization.realization.topologies:
            for realization in topology.realizations:
                unique.setdefault(self._gear_identity(realization), realization)
        return tuple(unique[key] for key in sorted(unique))

    def dual_bar_catalog(self) -> ExtremeDualBarGearStateCatalog:
        if self._dual_bar_catalog is None:
            self._dual_bar_catalog = ExtremeDualBarGearStateCatalogService.build(
                self._raw_gear_realizations(),
                source_denominator_proven=bool(self.gear_realization.denominator_proven),
                unresolved=tuple(self.gear_realization.unresolved),
            )
        return self._dual_bar_catalog

    def gear_realizations(self, *, active_bar: str = "front") -> tuple[ExtremeNamedGearSetRealization, ...]:
        return self.dual_bar_catalog().admissible_realizations(active_bar=active_bar)

    def armor_states(self) -> tuple[ExtremeArmorResourceWeightTraitGlyphState, ...]:
        return tuple(sorted(self.armor_catalog.states, key=self._armor_identity))

    @property
    def unresolved(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                (
                    *self.gear_realization.unresolved,
                    *self.dual_bar_catalog().unresolved,
                    *self.armor_catalog.unresolved,
                )
            )
        )

    @property
    def gear_denominator_proven(self) -> bool:
        return bool(self.dual_bar_catalog().denominator_proven)

    @property
    def reviewed_resource_armor_denominator_proven(self) -> bool:
        return bool(self.armor_catalog.denominator_proven)

    def _champion_point_state(self, objective_key: str):
        resolver = getattr(self.evaluator_factory, "champion_point_state", None)
        if not callable(resolver):
            return None
        return resolver(objective_key)

    def _active_skill_audit(self, objective_key: str):
        resolver = getattr(self.evaluator_factory, "active_skill_audit", None)
        if not callable(resolver):
            return None
        return resolver(objective_key)

    def closed_dynamic_axes(self, objective_key: str) -> tuple[str, ...]:
        closed: list[str] = []
        cp_state = self._champion_point_state(objective_key)
        if cp_state is not None and cp_state.denominator_proven and not cp_state.unresolved:
            closed.append("Champion Points")
        skill_audit = self._active_skill_audit(objective_key)
        if skill_audit is not None and skill_audit.projection_complete:
            closed.append("skill-bar choices and morphs")
        return tuple(closed)

    def additional_search_scope(self, objective_key: str) -> tuple[str, ...]:
        scope: list[str] = []
        cp_state = self._champion_point_state(objective_key)
        if cp_state is not None and cp_state.denominator_proven and not cp_state.unresolved:
            scope.append(_RESOURCE_CHAMPION_POINT_SCOPE)
        skill_audit = self._active_skill_audit(objective_key)
        if skill_audit is not None and skill_audit.projection_complete:
            scope.append(_RESOURCE_ACTIVE_SKILL_SCOPE)
        return tuple(scope)

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

        active_bar = str(getattr(candidate, "active_bar", "front") or "front").strip().casefold()
        gear_rows = self.gear_realizations(active_bar=active_bar)
        armor_rows = self.armor_states()
        if not gear_rows:
            raise ValueError("Extreme named gear search produced no dual-bar-admissible gear candidate")
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
        dual_catalog = self.dual_bar_catalog()
        best_payload["gear_candidates_scored"] = len(gear_rows)
        best_payload["resource_armor_states_scored"] = len(armor_rows)
        best_payload["gear_resource_armor_candidates_scored"] = len(gear_rows) * len(armor_rows)
        best_payload["dual_bar_gear_states_reviewed"] = len(dual_catalog.states)
        best_payload["dual_bar_compatible_pairs_reviewed"] = dual_catalog.compatible_pairs_reviewed
        best_payload["active_snapshot_gear_candidates_reviewed"] = dual_catalog.active_snapshots_reviewed
        best_payload["dual_bar_gear_denominator_proven"] = dual_catalog.denominator_proven
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
