from __future__ import annotations

from types import SimpleNamespace

from minmax.character_build.saved_build_adapter import SavedBuildAdaptation
from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.rotation_plan import RotationPlan
from services.extreme_runtime_snapshot import ExtremeRuntimePotionUse, ExtremeRuntimeSnapshot
from services.minmax_character_progression_adapter import SavedBuildProgressionResolution
from ui.rotation_canonical_candidate_support import RotationCanonicalCandidateSupport
from ui.rotation_recovery_validation_support import RotationRecoveryValidationScope
from ui.rotation_runtime_snapshot_candidate_support import (
    RotationRuntimeSnapshotCandidateSupport,
)


class _BuildAdapter:
    def __init__(self) -> None:
        self.calls = []
        self.canonical_build = object()

    def adapt(self, build, *, character_id=None):
        self.calls.append((build, character_id))
        return SavedBuildAdaptation(build=self.canonical_build, unresolved=())


class _ProgressionAdapter:
    def __init__(self) -> None:
        self.calls = []
        self.resolution = SavedBuildProgressionResolution(
            character_id="character-1",
            progression=CharacterProgression(passive_ranks={}),
            unresolved=(),
        )

    def resolve(self, build):
        self.calls.append(build)
        return self.resolution


class _StaticContextService:
    def __init__(self, progression_adapter) -> None:
        self.progression_adapter = progression_adapter


class _ExecutionChain:
    def __init__(self) -> None:
        self.calls = []
        self.result = object()

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _RuntimeStateService:
    def __init__(self, *, combat_state=None, unresolved=()) -> None:
        self.calls = []
        self.combat_state = combat_state or CombatState(
            in_combat=True,
            active_buffs=("Major Sorcery",),
        )
        self.unresolved = tuple(unresolved)

    def resolve(self, build, **kwargs):
        self.calls.append((build, kwargs))
        return SimpleNamespace(
            combat_state=self.combat_state,
            unresolved=self.unresolved,
        )


class _PlanRuntimeStateService:
    def __init__(self) -> None:
        self.calls = []
        self.result = object()

    def resolve(self, build, **kwargs):
        self.calls.append((build, kwargs))
        return self.result


def _support(*, runtime_state=None, plan_runtime_state=None):
    build_adapter = _BuildAdapter()
    progression_adapter = _ProgressionAdapter()
    canonical = RotationCanonicalCandidateSupport(
        build_adapter=build_adapter,
        static_context_service=_StaticContextService(progression_adapter),
    )
    execution = _ExecutionChain()
    runtime = runtime_state or _RuntimeStateService()
    plan_runtime = plan_runtime_state or _PlanRuntimeStateService()
    support = RotationRuntimeSnapshotCandidateSupport(
        canonical_candidates=execution,
        base_canonical=canonical,
        runtime_snapshot_state=runtime,
        plan_runtime_state=plan_runtime,
    )
    return (
        support,
        execution,
        runtime,
        plan_runtime,
        build_adapter,
        progression_adapter,
    )


def test_without_runtime_snapshot_delegates_without_projection() -> None:
    support, execution, runtime, plan_runtime, _, progression = _support()
    build = object()

    result = support.run_effects(player_build=build, marker="plain")

    assert result is execution.result
    assert execution.calls == [{"player_build": build, "marker": "plain"}]
    assert runtime.calls == []
    assert plan_runtime.calls == []
    assert progression.calls == []


def test_runtime_snapshot_requires_explicit_active_bar() -> None:
    support, execution, runtime, plan_runtime, _, _ = _support()
    build = object()

    result = support.run_effects(
        player_build=build,
        runtime_snapshot=ExtremeRuntimeSnapshot(snapshot_time_seconds=5.0),
    )

    assert execution.calls == []
    assert runtime.calls == []
    assert plan_runtime.calls == []
    assert result.pipeline_result is None
    assert result.validation.scope is RotationRecoveryValidationScope.NOT_EVALUATED
    assert result.validation.selectable is None
    assert any("runtime_snapshot_active_bar" in reason for reason in result.validation.reasons)


def test_runtime_snapshot_projects_shared_combat_state_into_execution_chain() -> None:
    projected_state = CombatState(
        in_combat=True,
        active_buffs=("Major Sorcery", "Major Prophecy"),
        game_update="U51",
        is_emperor=True,
        in_home_campaign=True,
        emperor_home_keeps=3,
    )
    runtime_state = _RuntimeStateService(combat_state=projected_state)
    support, execution, runtime, plan_runtime, _, progression = _support(
        runtime_state=runtime_state
    )
    build = object()
    base_state = CombatState(game_update="U51", is_emperor=True, in_home_campaign=True)
    snapshot = ExtremeRuntimeSnapshot(snapshot_time_seconds=12.0)

    result = support.run_effects(
        player_build=build,
        combat_state=base_state,
        runtime_snapshot=snapshot,
        runtime_snapshot_active_bar="BACK",
        marker="projected",
    )

    assert result is execution.result
    assert progression.calls == [build]
    assert len(runtime.calls) == 1
    projected_build, call = runtime.calls[0]
    assert projected_build is build
    assert call["progression"] is progression.resolution.progression
    assert call["active_bar"] == "back"
    assert call["snapshot"] is snapshot
    assert call["base_combat_state"] is base_state
    assert execution.calls[0]["combat_state"] is projected_state
    assert execution.calls[0]["marker"] == "projected"
    assert "runtime_snapshot" not in execution.calls[0]
    assert "runtime_snapshot_active_bar" not in execution.calls[0]
    assert "runtime_combat_state_resolver_factory" not in execution.calls[0]
    assert plan_runtime.calls == []


def test_unified_runtime_history_binds_final_plan_state_resolver() -> None:
    plan_runtime = _PlanRuntimeStateService()
    support, execution, _, _, _, progression = _support(
        plan_runtime_state=plan_runtime
    )
    build = object()
    base_state = CombatState(game_update="U51", is_emperor=True)
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(ExtremeRuntimePotionUse(time_seconds=3.0, sequence=1),),
        snapshot_time_seconds=8.0,
    )

    result = support.run_effects(
        player_build=build,
        combat_state=base_state,
        runtime_snapshot=snapshot,
        runtime_snapshot_active_bar="front",
        initial_bar="BACK",
    )

    assert result is execution.result
    factory = execution.calls[0]["runtime_combat_state_resolver_factory"]
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=(),
    )
    resolver = factory(plan)
    resolved = resolver(12.0, 4)

    assert resolved is plan_runtime.result
    assert len(plan_runtime.calls) == 1
    projected_build, call = plan_runtime.calls[0]
    assert projected_build is build
    assert call["progression"] is progression.resolution.progression
    assert call["plan"] is plan
    assert call["runtime_snapshot_source"] is snapshot
    assert call["time_seconds"] == 12.0
    assert call["sequence"] == 4
    assert call["initial_bar"] == "BACK"
    assert call["base_combat_state"] is base_state


def test_unresolved_runtime_projection_blocks_candidate_execution() -> None:
    runtime_state = _RuntimeStateService(
        unresolved=("gear proc target applicability unresolved",),
    )
    support, execution, runtime, plan_runtime, _, _ = _support(runtime_state=runtime_state)

    result = support.run_effects(
        player_build=object(),
        runtime_snapshot=ExtremeRuntimeSnapshot(snapshot_time_seconds=8.0),
        runtime_snapshot_active_bar="front",
    )

    assert len(runtime.calls) == 1
    assert execution.calls == []
    assert plan_runtime.calls == []
    assert result.pipeline_result is None
    assert result.validation.scope is RotationRecoveryValidationScope.NOT_EVALUATED
    assert result.validation.selectable is None
    assert any(
        "gear proc target applicability unresolved" in reason
        for reason in result.validation.reasons
    )
