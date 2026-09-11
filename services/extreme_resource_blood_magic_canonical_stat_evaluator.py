from __future__ import annotations

"""Score reviewed Blood Magic active-bar/runtime witnesses canonically.

This wrapper does not reproduce the resource evaluator. It asks the existing
resource-armor evaluator to score each proof-reduced active-bar witness, then only
for a witness carrying a proven positive-cost Dark Magic trigger performs the
reviewed two-pass Blood Magic context rebuild. The highest canonical objective
value wins.
"""

from dataclasses import replace
from typing import Any

from minmax.character_progression import CharacterProgression
from minmax.combat_effect_semantics import GameUpdate
from minmax.combat_state import CombatState
from models.build_model import PlayerBuild
from services.extreme_named_gear_resource_armor_canonical_stat_evaluator import (
    ExtremeNamedGearResourceArmorCanonicalStatEvaluator,
)
from services.extreme_resource_active_bar_state_service import (
    ExtremeResourceActiveBarState,
    ExtremeResourceActiveBarStateCatalog,
    ExtremeResourceActiveBarStateService,
)
from services.extreme_resource_blood_magic_runtime_context_service import (
    ExtremeResourceBloodMagicRuntimeContextService,
)
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate


class _FixedActiveBarStateService:
    def __init__(
        self,
        *,
        state: ExtremeResourceActiveBarState,
        source_catalog: ExtremeResourceActiveBarStateCatalog,
    ) -> None:
        self.state = state
        self.source_catalog = source_catalog

    def build(self, objective_key, _route):
        key = str(objective_key or "").strip().casefold()
        if key != self.state.objective_key:
            raise ValueError(
                f"fixed Extreme resource bar objective mismatch: {self.state.objective_key!r} != {key!r}"
            )
        return ExtremeResourceActiveBarStateCatalog(
            objective_key=key,
            states=(self.state,),
            active_skills_reviewed=self.source_catalog.active_skills_reviewed,
            denominator_proven=self.source_catalog.denominator_proven,
            unresolved=self.source_catalog.unresolved,
        )

    @staticmethod
    def materialize(build, state, *, active_bar):
        return ExtremeResourceActiveBarStateService.materialize(
            build,
            state,
            active_bar=active_bar,
        )


class ExtremeResourceBloodMagicCanonicalStatEvaluator:
    """Compare ordinary and Blood Magic bar/runtime continuations."""

    def __init__(
        self,
        *,
        evaluator: ExtremeNamedGearResourceArmorCanonicalStatEvaluator,
        active_bar_state_service: ExtremeResourceActiveBarStateService,
        blood_magic_runtime_context_service: ExtremeResourceBloodMagicRuntimeContextService | None = None,
        database_path=None,
    ) -> None:
        self.evaluator = evaluator
        self.active_bar_state_service = active_bar_state_service
        self.blood_magic_runtime_context_service = (
            blood_magic_runtime_context_service
            or ExtremeResourceBloodMagicRuntimeContextService(database_path)
        )

    def _clone_for_state(
        self,
        state: ExtremeResourceActiveBarState,
        catalog: ExtremeResourceActiveBarStateCatalog,
    ) -> ExtremeNamedGearResourceArmorCanonicalStatEvaluator:
        base = self.evaluator
        return ExtremeNamedGearResourceArmorCanonicalStatEvaluator(
            evaluator=base.evaluator,
            armor_state=base.armor_state,
            jewelry_state=base.jewelry_state,
            undaunted_progression_service=base.undaunted_progression_service,
            resource_armor_progression_service=base.resource_armor_progression_service,
            active_bar_progression_service=base.active_bar_progression_service,
            active_bar_state_service=_FixedActiveBarStateService(
                state=state,
                source_catalog=catalog,
            ),
            max_health_runtime_state_service=base.max_health_runtime_state_service,
            max_health_runtime_context_service=base.max_health_runtime_context_service,
            racial_progression_service=base.racial_progression_service,
            context_factory=base.context_factory,
        )

    def _blood_magic_score(
        self,
        *,
        key: str,
        candidate: ExtremeStructuralCandidate,
        state: ExtremeResourceActiveBarState,
        value: float,
        payload: dict[str, Any],
        unresolved: tuple[str, ...],
        active_buffs: tuple[str, ...],
    ) -> tuple[float, dict[str, Any], tuple[str, ...]]:
        if key not in ("max_magicka", "max_stamina") or not state.blood_magic_trigger_skill:
            return value, payload, unresolved

        base = self.evaluator
        progression = CharacterProgression(
            attributes=candidate.attributes,
            passive_ranks={},
            passive_cp_points={},
        )
        progression = base.progression_service.normalize(progression, candidate.class_route)
        if base.racial_progression_service is not None:
            progression = base.racial_progression_service.normalize(progression, candidate.race)

        normalized_buffs = tuple(
            dict.fromkeys(
                str(value or "").strip()
                for value in active_buffs
                if str(value or "").strip()
            )
        )
        combat_state = (
            CombatState(active_buffs=normalized_buffs, game_update=GameUpdate.U50)
            if normalized_buffs
            else None
        )
        factory = base.context_factory or getattr(base.optimizer, "context_factory", None)
        if factory is None:
            return value, payload, tuple(
                dict.fromkeys((*unresolved, "Blood Magic requires a canonical context factory"))
            )

        build = PlayerBuild.from_dict(payload["build"])
        character_id = "extreme-resource-blood-magic-runtime"
        build_id = f"{character_id}:{candidate.identity}:{state.identity}"
        context, blood_unresolved, selected_resource = self.blood_magic_runtime_context_service.resolve(
            factory=factory,
            build=build,
            progression=progression,
            objective_key=key,
            trigger_ability_name=state.blood_magic_trigger_skill,
            character_id=character_id,
            build_id=build_id,
            active_bar=candidate.active_bar,
            combat_state=combat_state,
        )
        objective = base.optimizer.objective(key)
        scored = float(base.optimizer._objective_value(context, objective))
        output = dict(payload)
        output["resource_blood_magic_trigger_skill"] = state.blood_magic_trigger_skill
        output["resource_blood_magic_selected_resource"] = selected_resource or ""
        output["resource_blood_magic_window_applied"] = selected_resource == key
        output["resource_blood_magic_window_percent"] = 0.10 if selected_resource == key else 0.0
        combined_unresolved = tuple(
            dict.fromkeys(
                str(item)
                for item in (
                    *unresolved,
                    *blood_unresolved,
                    *tuple(context.unresolved_gear_effects),
                )
                if str(item)
            )
        )
        return scored, output, combined_unresolved

    def evaluate_candidate(
        self,
        objective_key: str,
        candidate: ExtremeStructuralCandidate,
        *,
        mundus: str = "",
        food: str = "",
        potion: str = "",
        active_buffs: tuple[str, ...] = (),
    ) -> tuple[float, dict[str, Any], tuple[str, ...]]:
        key = str(objective_key or "").strip().casefold()
        catalog = self.active_bar_state_service.build(key, candidate.class_route)
        if not catalog.states:
            raise ValueError("Extreme resource active-bar search produced no witness state")

        best: tuple[float, dict[str, Any], tuple[str, ...]] | None = None
        best_identity: tuple[object, ...] | None = None
        for state in catalog.states:
            scorer = self._clone_for_state(state, catalog)
            value, payload, unresolved = scorer.evaluate_candidate(
                key,
                candidate,
                mundus=mundus,
                food=food,
                potion=potion,
                active_buffs=active_buffs,
            )
            value, payload, unresolved = self._blood_magic_score(
                key=key,
                candidate=candidate,
                state=state,
                value=float(value),
                payload=payload,
                unresolved=unresolved,
                active_buffs=active_buffs,
            )
            identity = tuple(state.identity)
            if (
                best is None
                or value > best[0] + 1e-9
                or (abs(value - best[0]) <= 1e-9 and (best_identity is None or identity < best_identity))
            ):
                best = (float(value), dict(payload), tuple(unresolved))
                best_identity = identity

        if best is None:
            raise ValueError("Extreme Blood Magic resource search produced no scored bar witness")
        value, payload, unresolved = best
        payload["resource_active_bar_states_scored"] = len(catalog.states)
        payload["resource_active_bar_denominator_proven"] = bool(catalog.denominator_proven)
        return value, payload, unresolved
