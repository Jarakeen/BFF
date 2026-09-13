from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from minmax.runtime_event import RuntimeEvent
from models.build_model import PlayerBuild
from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RecoveryHeavyCandidateOrchestrationInput,
    RotationRecoveryHeavyCandidateOrchestrationService,
)


def _plan(candidate_id: str) -> RotationPlan:
    return RotationPlan(
        character_name="Rotation Test",
        build_name=candidate_id,
        duration_seconds=20.0,
        actions=(),
    )


class _Stabilizer:
    def stabilize(self, **kwargs):
        plan = kwargs["generate"](None)
        replay = SimpleNamespace(final_plan_id=plan.build_name)
        kwargs["evaluate_candidate"](plan, replay)
        return SimpleNamespace(
            plan=plan,
            replay=replay,
            converged=True,
            termination_reason="stable_fixed_point",
            tracked_hard_obligations_satisfied=True,
        )


def _candidate(candidate_id: str) -> RecoveryHeavyCandidateOrchestrationInput:
    return RecoveryHeavyCandidateOrchestrationInput(
        candidate_id=candidate_id,
        generate=lambda _pressure: _plan(candidate_id),
        evaluate_candidate=lambda _plan, _replay: SimpleNamespace(
            candidate_id=candidate_id
        ),
    )


def test_output_condition_context_factory_binds_only_after_final_plan_stabilization() -> None:
    service = RotationRecoveryHeavyCandidateOrchestrationService(
        stabilization_service=_Stabilizer()
    )
    factory_calls = []
    resolver_calls = []

    def condition_context_factory(plan):
        factory_calls.append(plan)

        def resolve(event):
            resolver_calls.append((plan, event))
            if float(event.time_seconds) == 4.0:
                return frozenset({"target_in_test_geometry"})
            return frozenset()

        return resolve

    observed = []

    def evaluate_final_family(snapshots):
        observed.extend(snapshots)
        snapshot = snapshots[0]
        assert snapshot.runtime_output_condition_context_resolver is not None
        event = RuntimeEvent(
            time_seconds=4.0,
            trigger="damage_dealt",
            source="test conditional output",
            sequence=1,
        )
        assert snapshot.runtime_output_condition_context_resolver(event) == frozenset(
            {"target_in_test_geometry"}
        )
        return (
            SimpleNamespace(
                candidate_id="final",
                tier=RotationCandidateTier.ELIGIBLE,
                rank=1,
                reasons=(),
            ),
        )

    result = service.orchestrate(
        build=PlayerBuild(Name="Rotation Test", BuildName="Role Neutral"),
        candidates=(_candidate("final"),),
        evaluate_final_family=evaluate_final_family,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
        restoration_resolver=lambda _heavy: None,
        runtime_output_condition_context_resolver_factory=condition_context_factory,
    )

    assert [plan.build_name for plan in factory_calls] == ["final"]
    assert [item.candidate_id for item in observed] == ["final"]
    assert len(resolver_calls) == 1
    assert resolver_calls[0][0] is factory_calls[0]
    assert result.stabilized_candidates[0].runtime_output_condition_context_resolver is not None
