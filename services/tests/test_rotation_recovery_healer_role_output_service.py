from types import SimpleNamespace

from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateRoleOutputEvidence,
)
from services.rotation_recovery_healer_role_output_service import (
    RotationRecoveryHealerRoleOutputService,
)
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RecoveryHeavyStabilizedCandidateSnapshot,
)


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Healer Tester",
        build_name="Runtime Healer",
        duration_seconds=30.0,
        actions=(),
    )


class _RoleOutputService:
    def __init__(self) -> None:
        self.calls = []

    def evaluate_plan(self, candidate, **kwargs):
        self.calls.append((candidate, kwargs))
        resolver = kwargs.get("runtime_build_context_resolver")
        if resolver is not None:
            resolved = resolver(12.0, 2)
            assert resolved.context == "runtime-context"
        return RotationCandidateRoleOutputEvidence(
            candidate_id=candidate.candidate_id,
            value=321.0,
        )


class _RuntimeBuildContextService:
    def __init__(self) -> None:
        self.calls = []

    def resolve(self, build, **kwargs):
        self.calls.append((build, kwargs))
        runtime = kwargs["runtime_combat_state_resolver"](
            kwargs["time_seconds"],
            kwargs["sequence"],
        )
        assert runtime == "combat-state-at-12-seq-2"
        return SimpleNamespace(context="runtime-context")


def _snapshot(*, runtime_resolver=None):
    return RecoveryHeavyStabilizedCandidateSnapshot(
        candidate_id="final-healer",
        plan=_plan(),
        replay=object(),
        stabilization=object(),
        runtime_combat_state_resolver=runtime_resolver,
    )


def test_final_healer_snapshot_without_runtime_history_keeps_static_role_output_path() -> None:
    role_output = _RoleOutputService()
    runtime_context = _RuntimeBuildContextService()
    service = RotationRecoveryHealerRoleOutputService(
        build=PlayerBuild(),
        role_output_service=role_output,
        runtime_build_context_service=runtime_context,
    )

    result = service.evaluate_snapshot(_snapshot())

    assert result.candidate_id == "final-healer"
    assert result.resolved_value == 321.0
    assert len(role_output.calls) == 1
    candidate, kwargs = role_output.calls[0]
    assert candidate.candidate_id == "final-healer"
    assert candidate.plan.build_name == "Runtime Healer"
    assert kwargs == {}
    assert runtime_context.calls == []


def test_final_healer_snapshot_binds_exact_runtime_context_after_stabilization() -> None:
    build = PlayerBuild()
    role_output = _RoleOutputService()
    runtime_context = _RuntimeBuildContextService()
    runtime_calls = []

    def runtime_state(time_seconds, sequence=None):
        runtime_calls.append((time_seconds, sequence))
        return "combat-state-at-12-seq-2"

    service = RotationRecoveryHealerRoleOutputService(
        build=build,
        role_output_service=role_output,
        runtime_build_context_service=runtime_context,
    )

    result = service.evaluate_snapshot(
        _snapshot(runtime_resolver=runtime_state)
    )

    assert result.candidate_id == "final-healer"
    assert result.resolved_value == 321.0
    assert runtime_calls == [(12.0, 2)]
    assert len(runtime_context.calls) == 1
    resolved_build, call = runtime_context.calls[0]
    assert resolved_build is build
    assert call["runtime_combat_state_resolver"] is runtime_state
    assert call["time_seconds"] == 12.0
    assert call["sequence"] == 2
    assert len(role_output.calls) == 1
    candidate, kwargs = role_output.calls[0]
    assert candidate.plan is not None
    assert kwargs["runtime_build_context_resolver"] is not None
