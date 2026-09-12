from types import SimpleNamespace

import pytest

from services.rotation_candidate_recommendation_evidence_service import (
    RotationCandidatePlanEvidence,
)
from services.rotation_gameplay_policy_assessment_service import (
    RotationGameplayPolicyContext,
    RotationGameplayPolicyStatus,
)
from services.rotation_recovery_final_role_evidence_service import (
    RotationRecoveryFinalRoleEvidenceConfiguration,
    RotationRecoveryFinalRoleEvidenceService,
)


class _PlanEvidenceProvider:
    def __init__(self, *, role_output_value: float = 200_000.0) -> None:
        self.calls = []
        self.role_output_value = float(role_output_value)

    def evaluate_plan(self, candidate):
        self.calls.append(candidate)
        return RotationCandidatePlanEvidence(
            sustain=object(),
            role_output_value=self.role_output_value,
            assigned_support_value=0.75,
            sustain_margin=999_999.0,
            primary_role_displacement_seconds=1.25,
            role_hard_obligation_satisfied=True,
            role_hard_obligation_reasons=("verified DD assignment",),
        )


class _SnapshotAwarePlanEvidenceProvider:
    def __init__(self) -> None:
        self.static = _PlanEvidenceProvider(role_output_value=100_000.0)
        self.runtime = _PlanEvidenceProvider(role_output_value=250_000.0)
        self.snapshots = []

    def evaluate_plan(self, candidate):
        return self.static.evaluate_plan(candidate)

    def for_stabilized_snapshot(self, snapshot):
        self.snapshots.append(snapshot)
        return self.runtime


class _PolicyContextProvider:
    def __init__(self, *, candidate_id: str = "candidate") -> None:
        self.candidate_id = candidate_id
        self.calls = []

    def context_for(self, candidate):
        self.calls.append(candidate)
        return RotationGameplayPolicyContext(
            candidate_id=self.candidate_id,
            role="dd",
            content_type="trial",
            personal_heal_skill_slots=("front:Personal Heal",),
            reliable_group_healing=True,
        )


def _snapshot(candidate_id: str = "candidate"):
    plan = object()
    replay = SimpleNamespace(
        final_projection=SimpleNamespace(
            run=SimpleNamespace(
                sustain=SimpleNamespace(minimum_amount=4321),
            )
        )
    )
    return SimpleNamespace(candidate_id=candidate_id, plan=plan, replay=replay)


def _service(*, policy_provider=None):
    plan_evidence = _PlanEvidenceProvider()
    scorecard = object()
    service = RotationRecoveryFinalRoleEvidenceService(
        plan_evidence_provider=plan_evidence,
        scorecard_resolver=lambda _snapshot: scorecard,
        configuration=RotationRecoveryFinalRoleEvidenceConfiguration(
            role_key="dd",
            role_output_label="effective damage",
            assigned_support_label="assigned support coverage",
        ),
        gameplay_policy_context_provider=policy_provider,
    )
    return service, plan_evidence, scorecard


def test_final_role_evidence_uses_stabilized_replay_for_sustain_margin() -> None:
    policy = _PolicyContextProvider()
    service, plan_evidence, scorecard = _service(policy_provider=policy)
    snapshot = _snapshot()

    result = service.resolve(snapshot)

    assert result.candidate_id == "candidate"
    assert result.scorecard is scorecard
    assert result.role_key == "dd"
    assert result.role_output_value == pytest.approx(200_000.0)
    assert result.assigned_support_value == pytest.approx(0.75)
    assert result.primary_role_displacement_seconds == pytest.approx(1.25)
    assert result.role_hard_obligation_satisfied is True
    assert result.role_hard_obligation_reasons == ("verified DD assignment",)
    assert result.sustain_margin == pytest.approx(4321.0)
    assert result.gameplay_policy_assessment is not None
    assert (
        result.gameplay_policy_assessment.status
        is RotationGameplayPolicyStatus.DISFAVORED
    )

    assert len(plan_evidence.calls) == 1
    assert plan_evidence.calls[0].candidate_id == snapshot.candidate_id
    assert plan_evidence.calls[0].plan is snapshot.plan
    assert len(policy.calls) == 1
    assert policy.calls[0].plan is snapshot.plan


def test_final_role_evidence_binds_snapshot_aware_provider_after_stabilization() -> None:
    provider = _SnapshotAwarePlanEvidenceProvider()
    scorecard = object()
    service = RotationRecoveryFinalRoleEvidenceService(
        plan_evidence_provider=provider,
        scorecard_resolver=lambda _snapshot: scorecard,
        configuration=RotationRecoveryFinalRoleEvidenceConfiguration(
            role_key="dd",
            role_output_label="effective damage",
            assigned_support_label="assigned support coverage",
        ),
    )
    snapshot = _snapshot("runtime")

    result = service.resolve(snapshot)

    assert provider.snapshots == [snapshot]
    assert provider.static.calls == []
    assert len(provider.runtime.calls) == 1
    assert provider.runtime.calls[0].plan is snapshot.plan
    assert result.role_output_value == pytest.approx(250_000.0)


def test_final_role_evidence_without_policy_context_preserves_mechanical_role_evidence() -> None:
    service, _plan_evidence, _scorecard = _service(policy_provider=None)

    result = service.resolve(_snapshot())

    assert result.gameplay_policy_assessment is None
    assert result.role_output_value == pytest.approx(200_000.0)
    assert result.sustain_margin == pytest.approx(4321.0)


def test_final_role_evidence_rejects_policy_context_candidate_mismatch() -> None:
    service, _plan_evidence, _scorecard = _service(
        policy_provider=_PolicyContextProvider(candidate_id="different")
    )

    with pytest.raises(ValueError, match="gameplay-policy context candidate mismatch"):
        service.resolve(_snapshot())


def test_final_role_evidence_exposes_typed_resolver_contract() -> None:
    service, _plan_evidence, _scorecard = _service()
    resolver = service.resolver()

    result = resolver(_snapshot("resolved"))

    assert result.candidate_id == "resolved"
