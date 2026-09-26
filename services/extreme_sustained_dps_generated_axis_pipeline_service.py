from __future__ import annotations

"""Compose generated sustained-DPS adapter packs into one lazy indexed-axis pipeline.

Each adapter owns a different immutable state type. This service supplies the explicit
stage transitions needed to traverse gear, late build refinement, rotation planning,
and evidence-gated runtime policies in one branch-and-bound tree while preserving any
axis-local optimistic-bound provider.
"""

from dataclasses import dataclass, replace

from minmax.potion_cadence import BASE_POTION_COOLDOWN_SECONDS

from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSIndexedFrontierAxis,
)
from services.extreme_sustained_dps_generated_runtime_state_axis_adapter_service import (
    ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedAxisPipelineState:
    gear: object
    candidate_id_prefix: str
    duration_seconds: float
    potion_cooldown_seconds: float | None
    potion_cooldown_resolver: object | None
    potion_cooldown_scenario: object | None
    starting_ultimate: float
    ultimate_generation_events: tuple[object, ...]
    heroism_windows: tuple[object, ...]
    use_scheduled_combat_attacks_for_ultimate: bool
    priorities: object
    snapshot_resolver: object
    target_identity: str
    duration_rules: tuple[object, ...]
    heavy_attack_windows: tuple[object, ...]
    heavy_attack_channel_blocks: tuple[object, ...]
    heavy_attack_channel_block_denominator_proven: bool
    mundus_food: object | None = None
    late: object | None = None
    encounter_policy: object | None = None
    rotation: object | None = None
    runtime: object | None = None
    finalized_potion: object | None = None
    requires_finalized_potion: bool = False

    @property
    def complete(self) -> bool:
        if not isinstance(self.requires_finalized_potion, bool):
            raise TypeError(
                "generated axis pipeline requires_finalized_potion flag must be boolean"
            )
        stage = self.finalized_potion if self.requires_finalized_potion else self.runtime
        if stage is None:
            return False
        complete = getattr(stage, "complete", False)
        if not isinstance(complete, bool):
            raise TypeError("generated axis pipeline terminal complete flag must be boolean")
        return complete


class ExtremeSustainedDPSGeneratedAxisPipelineService:
    """Bridge four generated adapter state machines without flattening frontiers."""

    def __init__(
        self,
        *,
        gear_adapter: object,
        late_adapter: object,
        rotation_adapter: object,
        runtime_policy_adapter: object,
        mundus_food_adapter: object | None = None,
        encounter_policy_adapter: object | None = None,
        finalized_potion_adapter: object | None = None,
        finalized_potion_evidence_resolver: object | None = None,
        runtime_state_frontier_resolver: object | None = None,
    ) -> None:
        self.gear_adapter = gear_adapter
        self.mundus_food_adapter = mundus_food_adapter
        self.late_adapter = late_adapter
        self.encounter_policy_adapter = encounter_policy_adapter
        self.rotation_adapter = rotation_adapter
        self.runtime_policy_adapter = runtime_policy_adapter
        self.finalized_potion_adapter = finalized_potion_adapter
        self.finalized_potion_evidence_resolver = finalized_potion_evidence_resolver
        self.runtime_state_frontier_resolver = runtime_state_frontier_resolver

    @staticmethod
    def _require_complete(stage: object, label: str) -> None:
        complete = getattr(stage, "complete", False)
        if not isinstance(complete, bool):
            raise TypeError(f"generated {label} complete flag must be boolean")
        if not complete:
            raise ValueError(
                f"generated axis pipeline requires complete {label} selections"
            )

    def _gear_state(
        self,
        state: ExtremeSustainedDPSGeneratedAxisPipelineState,
    ) -> object:
        return state.gear

    def _mundus_food_state(
        self,
        state: ExtremeSustainedDPSGeneratedAxisPipelineState,
    ) -> object:
        if self.mundus_food_adapter is None:
            raise ValueError("generated axis pipeline has no Mundus/food adapter")
        if state.mundus_food is not None:
            return state.mundus_food
        self._require_complete(state.gear, "gear-axis")
        context = getattr(state.gear, "context", None)
        if context is None:
            raise ValueError(
                "complete generated gear-axis state is missing cross-axis context"
            )
        return self.mundus_food_adapter.root(context)

    def _late_state(
        self,
        state: ExtremeSustainedDPSGeneratedAxisPipelineState,
    ) -> object:
        if state.late is not None:
            return state.late
        if self.mundus_food_adapter is not None:
            mundus_food = self._mundus_food_state(state)
            self._require_complete(mundus_food, "Mundus/food-axis")
            context = getattr(mundus_food, "context", None)
            if context is None:
                raise ValueError(
                    "complete generated Mundus/food-axis state is missing cross-axis context"
                )
        else:
            self._require_complete(state.gear, "gear-axis")
            context = getattr(state.gear, "context", None)
            if context is None:
                raise ValueError(
                    "complete generated gear-axis state is missing cross-axis context"
                )
        return self.late_adapter.root(context)

    def _encounter_policy_state(
        self,
        state: ExtremeSustainedDPSGeneratedAxisPipelineState,
    ) -> object:
        if self.encounter_policy_adapter is None:
            raise ValueError("generated axis pipeline has no encounter-policy adapter")
        if state.encounter_policy is not None:
            return state.encounter_policy
        late = self._late_state(state)
        self._require_complete(late, "late-axis")
        assembled = getattr(late, "assembled", None)
        if assembled is None:
            raise ValueError(
                "complete generated late-axis state is missing assembled candidate"
            )
        return self.encounter_policy_adapter.root(assembled)

    def _resolved_potion_cooldown(
        self,
        state: ExtremeSustainedDPSGeneratedAxisPipelineState,
        assembled: object,
    ) -> float:
        build = getattr(assembled, "build", None)
        if hasattr(build, "Potion") and not str(getattr(build, "Potion", "") or "").strip():
            return float(BASE_POTION_COOLDOWN_SECONDS)
        if state.potion_cooldown_resolver is None:
            if state.potion_cooldown_seconds is None:
                raise ValueError("generated axis pipeline requires potion cooldown evidence")
            cooldown = float(state.potion_cooldown_seconds)
            if cooldown <= 0.0:
                raise ValueError("generated axis pipeline potion cooldown must be positive")
            return cooldown
        scenario = state.potion_cooldown_scenario
        resolution = state.potion_cooldown_resolver.resolve(
            player_build=assembled.build,
            progression=getattr(assembled, "progression", None),
            scenario=scenario,
        )
        complete = getattr(resolution, "complete", False)
        if not isinstance(complete, bool):
            raise TypeError("potion cooldown resolution complete flag must be boolean")
        unresolved = getattr(resolution, "unresolved", ())
        if not isinstance(unresolved, tuple):
            raise TypeError("potion cooldown resolution unresolved evidence must be a tuple")
        if not complete:
            detail = "; ".join(unresolved)
            raise ValueError(
                "generated axis pipeline potion cooldown is unresolved"
                + (f": {detail}" if detail else "")
            )
        cooldown = float(resolution.cooldown_seconds)
        if cooldown <= 0.0:
            raise ValueError("generated axis pipeline resolved potion cooldown must be positive")
        return cooldown

    def _rotation_state(
        self,
        state: ExtremeSustainedDPSGeneratedAxisPipelineState,
    ) -> object:
        if state.rotation is not None:
            return state.rotation

        encounter_demands: tuple[object, ...] = ()
        if self.encounter_policy_adapter is not None:
            encounter = self._encounter_policy_state(state)
            self._require_complete(encounter, "encounter-policy-axis")
            assembled = getattr(encounter, "assembled", None)
            choice = getattr(encounter, "choice", None)
            if assembled is None or choice is None:
                raise ValueError(
                    "complete generated encounter-policy state is missing assembled candidate or selected policy"
                )
            encounter_demands = tuple(getattr(choice, "demands", ()) or ())
        else:
            late = self._late_state(state)
            self._require_complete(late, "late-axis")
            assembled = getattr(late, "assembled", None)
            if assembled is None:
                raise ValueError(
                    "complete generated late-axis state is missing assembled candidate"
                )

        return self.rotation_adapter.root(
            assembled,
            duration_seconds=state.duration_seconds,
            potion_cooldown_seconds=self._resolved_potion_cooldown(state, assembled),
            starting_ultimate=state.starting_ultimate,
            ultimate_generation_events=state.ultimate_generation_events,
            heroism_windows=state.heroism_windows,
            use_scheduled_combat_attacks_for_ultimate=(
                state.use_scheduled_combat_attacks_for_ultimate
            ),
            priorities=state.priorities,
            encounter_demands=encounter_demands,
        )

    @staticmethod
    def _structural_index(value: object, label: str) -> int:
        raw = getattr(value, "structural_index", None)
        if raw is None:
            raise ValueError(
                f"complete generated rotation state is missing {label} structural index"
            )
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise TypeError(
                f"complete generated rotation state {label} structural index must be an integer"
            )
        return raw

    def _runtime_state(
        self,
        state: ExtremeSustainedDPSGeneratedAxisPipelineState,
    ) -> object:
        if state.runtime is not None:
            return state.runtime
        rotation = self._rotation_state(state)
        self._require_complete(rotation, "rotation-axis")
        plan = getattr(rotation, "rotation_plan", None)
        policy = getattr(rotation, "rotation_policy", None)
        if plan is None or policy is None:
            raise ValueError(
                "complete generated rotation-axis state is missing plan or policy"
            )
        candidate_id = (
            f"{state.candidate_id_prefix}"
            f"|rotation-plan:{self._structural_index(plan, 'plan')}"
            f"|anchored-policy:{self._structural_index(policy, 'policy')}"
        )
        return self.runtime_policy_adapter.root(
            policy,
            candidate_id=candidate_id,
            priorities=state.priorities,
            snapshot_resolver=state.snapshot_resolver,
            target_identity=state.target_identity,
            duration_rules=state.duration_rules,
            heavy_attack_windows=state.heavy_attack_windows,
            heavy_attack_channel_blocks=state.heavy_attack_channel_blocks,
            heavy_attack_channel_block_denominator_proven=(
                state.heavy_attack_channel_block_denominator_proven
            ),
        )

    def _finalized_potion_state(
        self,
        state: ExtremeSustainedDPSGeneratedAxisPipelineState,
    ) -> object:
        if self.finalized_potion_adapter is None:
            raise ValueError("generated axis pipeline has no finalized-potion adapter")
        if self.finalized_potion_evidence_resolver is None:
            raise ValueError(
                "generated axis pipeline finalized-potion adapter requires timing-evidence resolver"
            )
        if state.finalized_potion is not None:
            return state.finalized_potion

        runtime = self._runtime_state(state)
        self._require_complete(runtime, "runtime-policy-axis")

        late = self._late_state(state)
        self._require_complete(late, "late-axis")
        assembled = getattr(late, "assembled", None)
        if assembled is None:
            raise ValueError(
                "complete generated late-axis state is missing assembled candidate"
            )

        return self.finalized_potion_adapter.root(
            state,
            build=assembled.build,
            progression=assembled.progression,
            potion_cooldown_seconds=self._resolved_potion_cooldown(state, assembled),
            evidence_resolver=self.finalized_potion_evidence_resolver,
        )

    @staticmethod
    def _replace_gear(
        state: ExtremeSustainedDPSGeneratedAxisPipelineState,
        stage: object,
    ) -> ExtremeSustainedDPSGeneratedAxisPipelineState:
        return replace(
            state,
            gear=stage,
            mundus_food=None,
            late=None,
            encounter_policy=None,
            rotation=None,
            runtime=None,
            finalized_potion=None,
        )

    @staticmethod
    def _replace_mundus_food(
        state: ExtremeSustainedDPSGeneratedAxisPipelineState,
        stage: object,
    ) -> ExtremeSustainedDPSGeneratedAxisPipelineState:
        return replace(
            state,
            mundus_food=stage,
            late=None,
            encounter_policy=None,
            rotation=None,
            runtime=None,
            finalized_potion=None,
        )

    @staticmethod
    def _replace_late(
        state: ExtremeSustainedDPSGeneratedAxisPipelineState,
        stage: object,
    ) -> ExtremeSustainedDPSGeneratedAxisPipelineState:
        return replace(
            state,
            late=stage,
            encounter_policy=None,
            rotation=None,
            runtime=None,
            finalized_potion=None,
        )

    @staticmethod
    def _replace_encounter_policy(
        state: ExtremeSustainedDPSGeneratedAxisPipelineState,
        stage: object,
    ) -> ExtremeSustainedDPSGeneratedAxisPipelineState:
        return replace(
            state,
            encounter_policy=stage,
            rotation=None,
            runtime=None,
            finalized_potion=None,
        )

    @staticmethod
    def _replace_rotation(
        state: ExtremeSustainedDPSGeneratedAxisPipelineState,
        stage: object,
    ) -> ExtremeSustainedDPSGeneratedAxisPipelineState:
        return replace(
            state,
            rotation=stage,
            runtime=None,
            finalized_potion=None,
        )

    @staticmethod
    def _replace_runtime(
        state: ExtremeSustainedDPSGeneratedAxisPipelineState,
        stage: object,
    ) -> ExtremeSustainedDPSGeneratedAxisPipelineState:
        return replace(state, runtime=stage, finalized_potion=None)

    @staticmethod
    def _replace_finalized_potion(
        state: ExtremeSustainedDPSGeneratedAxisPipelineState,
        stage: object,
    ) -> ExtremeSustainedDPSGeneratedAxisPipelineState:
        return replace(state, finalized_potion=stage)

    @staticmethod
    def _wrap_axis(
        axis: ExtremeSustainedDPSIndexedFrontierAxis,
        *,
        stage_getter,
        stage_replacer,
    ) -> ExtremeSustainedDPSIndexedFrontierAxis:
        def candidate_count(state):
            return axis.candidate_count(stage_getter(state))

        def candidate_at(state, index):
            stage = stage_getter(state)
            return stage_replacer(state, axis.candidate_at(stage, index))

        bound_inputs = None
        if axis.bound_inputs is not None:
            def bound_inputs(state):
                return axis.bound_inputs(stage_getter(state))

        return ExtremeSustainedDPSIndexedFrontierAxis(
            axis.name,
            candidate_count=candidate_count,
            candidate_at=candidate_at,
            bound_inputs=bound_inputs,
            canonical_axes=axis.canonical_axes,
            omitted_scope=axis.omitted_scope,
        )

    def root(
        self,
        build: object,
        progression: object,
        *,
        dual_bar_frontier: object,
        candidate_id_prefix: str,
        duration_seconds: float,
        potion_cooldown_seconds: float | None,
        starting_ultimate: float,
        potion_cooldown_resolver: object | None = None,
        potion_cooldown_scenario: object | None = None,
        priorities: object,
        snapshot_resolver: object,
        target_identity: str,
        ultimate_generation_events: tuple[object, ...] = (),
        heroism_windows: tuple[object, ...] = (),
        use_scheduled_combat_attacks_for_ultimate: bool = False,
        duration_rules: tuple[object, ...] = (),
        heavy_attack_windows: tuple[object, ...] = (),
        heavy_attack_channel_blocks: tuple[object, ...] = (),
        heavy_attack_channel_block_denominator_proven: bool = False,
    ) -> ExtremeSustainedDPSGeneratedAxisPipelineState:
        prefix = str(candidate_id_prefix or "").strip()
        if not prefix:
            raise ValueError("generated axis pipeline candidate_id_prefix is required")
        if isinstance(duration_seconds, bool):
            raise TypeError("generated axis pipeline duration must be numeric, not boolean")
        if isinstance(potion_cooldown_seconds, bool):
            raise TypeError("generated axis pipeline potion cooldown must be numeric, not boolean")
        if isinstance(starting_ultimate, bool):
            raise TypeError("generated axis pipeline starting Ultimate must be numeric, not boolean")
        if not isinstance(use_scheduled_combat_attacks_for_ultimate, bool):
            raise TypeError("generated axis pipeline scheduled-combat Ultimate flag must be boolean")
        if not isinstance(heavy_attack_channel_block_denominator_proven, bool):
            raise TypeError("generated axis pipeline Heavy Attack denominator proof flag must be boolean")
        gear = self.gear_adapter.root(
            build,
            progression,
            dual_bar_frontier=dual_bar_frontier,
        )
        return ExtremeSustainedDPSGeneratedAxisPipelineState(
            gear=gear,
            candidate_id_prefix=prefix,
            duration_seconds=float(duration_seconds),
            potion_cooldown_seconds=(
                None if potion_cooldown_seconds is None else float(potion_cooldown_seconds)
            ),
            potion_cooldown_resolver=potion_cooldown_resolver,
            potion_cooldown_scenario=potion_cooldown_scenario,
            starting_ultimate=float(starting_ultimate),
            ultimate_generation_events=tuple(ultimate_generation_events),
            heroism_windows=tuple(heroism_windows),
            use_scheduled_combat_attacks_for_ultimate=use_scheduled_combat_attacks_for_ultimate,
            priorities=priorities,
            snapshot_resolver=snapshot_resolver,
            target_identity=str(target_identity or "").strip(),
            duration_rules=tuple(duration_rules),
            heavy_attack_windows=tuple(heavy_attack_windows),
            heavy_attack_channel_blocks=tuple(heavy_attack_channel_blocks),
            heavy_attack_channel_block_denominator_proven=heavy_attack_channel_block_denominator_proven,
            requires_finalized_potion=bool(self.finalized_potion_adapter is not None),
        )

    def axes(self) -> tuple[ExtremeSustainedDPSIndexedFrontierAxis, ...]:
        groups = [
            (
                self.gear_adapter.axes(),
                self._gear_state,
                self._replace_gear,
            ),
        ]
        if self.mundus_food_adapter is not None:
            groups.append(
                (
                    self.mundus_food_adapter.axes(),
                    self._mundus_food_state,
                    self._replace_mundus_food,
                )
            )
        groups.append(
            (
                self.late_adapter.axes(),
                self._late_state,
                self._replace_late,
            )
        )
        if self.encounter_policy_adapter is not None:
            groups.append(
                (
                    self.encounter_policy_adapter.axes(),
                    self._encounter_policy_state,
                    self._replace_encounter_policy,
                )
            )
        groups.extend(
            (
                (
                    self.rotation_adapter.axes(),
                    self._rotation_state,
                    self._replace_rotation,
                ),
                (
                    self.runtime_policy_adapter.axes(),
                    self._runtime_state,
                    self._replace_runtime,
                ),
            )
        )
        if self.finalized_potion_adapter is not None:
            groups.append(
                (
                    (self.finalized_potion_adapter.axis(),),
                    self._finalized_potion_state,
                    self._replace_finalized_potion,
                )
            )
        axes = tuple(
            self._wrap_axis(
                axis,
                stage_getter=getter,
                stage_replacer=replacer,
            )
            for axes, getter, replacer in groups
            for axis in axes
        )
        if self.runtime_state_frontier_resolver is not None:
            axes = (
                *axes,
                ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService.candidate_axis(
                    self.runtime_state_frontier_resolver
                ),
            )
        return axes


__all__ = [
    "ExtremeSustainedDPSGeneratedAxisPipelineService",
    "ExtremeSustainedDPSGeneratedAxisPipelineState",
]
