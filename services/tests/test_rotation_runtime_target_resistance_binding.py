from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RecoveryHeavyCandidateOrchestrationInput,
    RotationRecoveryHeavyCandidateOrchestrationService,
)


class _Stabilizer:
    def stabilize(
        self,
        *,
        build,
        generate,
        evaluate_candidate,
        resource,
        maximum_amount,
        trigger_fraction,
        restoration_resolver,
        reserve_assessment_resolver=None,
        max_iterations=6,
        calculation_context=None,
        maximum_event_resolver=None,
        displayed_recovery_resolver_factory=None,
    ):
        plan = generate(None)
        replay = SimpleNamespace()
        evaluate_candidate(plan, replay)
        return SimpleNamespace(
            plan=plan,
            replay=replay,
            converged=True,
            termination_reason="stable_fixed_point",
            tracked_hard_obligations_satisfied=True,
        )


def test_runtime_target_resistance_factory_binds_to_final_stabilized_plan() -> None:
    final_plan = RotationPlan(
        character_name="Resistance Test",
        build_name="final-resistance-plan",
        duration_seconds=12.0,
        actions=(),
    )
    factory_calls = []
    resolver_calls = []

    def target_resistance_factory(plan):
        factory_calls.append(plan)

        def resolve(time_seconds, sequence=None):
            resolver_calls.append((plan, time_seconds, sequence))
            return 12345.0

        return resolve

    candidate = RecoveryHeavyCandidateOrchestrationInput(
        candidate_id="target-resistance",
        generate=lambda _pressure: final_plan,
        evaluate_candidate=lambda _plan, _replay: SimpleNamespace(
            candidate_id="target-resistance"
        ),
    )

    def evaluate_final_family(snapshots):
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        assert snapshot.runtime_target_resistance_resolver is not None
        assert snapshot.runtime_target_resistance_resolver(4.0, 2) == 12345.0
        return (
            SimpleNamespace(
                candidate_id="target-resistance",
                tier=RotationCandidateTier.ELIGIBLE,
                rank=1,
                reasons=(),
            ),
        )

    result = RotationRecoveryHeavyCandidateOrchestrationService(
        stabilization_service=_Stabilizer(),
    ).orchestrate(
        build=PlayerBuild(Name="Resistance Test", BuildName="DD"),
        candidates=(candidate,),
        evaluate_final_family=evaluate_final_family,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
        restoration_resolver=lambda _heavy: None,
        runtime_target_resistance_resolver_factory=target_resistance_factory,
    )

    assert factory_calls == [final_plan]
    assert resolver_calls == [(final_plan, 4.0, 2)]
    assert result.stabilized_candidates[0].runtime_target_resistance_resolver is not None
