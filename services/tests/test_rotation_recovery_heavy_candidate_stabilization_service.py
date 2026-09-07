from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingResult,
    RotationCandidateTier,
)
from services.rotation_recovery_heavy_candidate_stabilization_service import (
    RotationRecoveryHeavyCandidateStabilizationService,
)


class _FakeHardStateService:
    def __init__(self) -> None:
        self.results = []

    def from_ranking_result(self, result):
        self.results.append(result)
        return (f"hard:{result.candidate_id}",)

    def from_effect_ranking_result(self, result):
        raise AssertionError("effect path not expected in this test")


class _FakeStabilizationService:
    def __init__(self) -> None:
        self.kwargs = None
        self.observed_state = None

    def stabilize(self, **kwargs):
        self.kwargs = kwargs
        plan = SimpleNamespace(name="generated plan")
        replay = SimpleNamespace(name="replayed sustain")
        self.observed_state = kwargs["hard_obligation_state_resolver"](plan, replay)
        return SimpleNamespace(converged=True, termination_reason="stable_fixed_point")


def test_candidate_evaluation_is_replayed_into_fixed_point_hard_state() -> None:
    stabilization = _FakeStabilizationService()
    hard_state = _FakeHardStateService()
    service = RotationRecoveryHeavyCandidateStabilizationService(
        stabilization_service=stabilization,
        hard_state_service=hard_state,
    )
    evaluations = []

    def evaluate_candidate(plan, replay):
        evaluations.append((plan, replay))
        return RotationCandidateRankingResult(
            candidate_id="candidate-a",
            scorecard=SimpleNamespace(),
            tier=RotationCandidateTier.INELIGIBLE,
            rank=1,
            reasons=("presentation text is not the fixed-point contract",),
        )

    result = service.stabilize(
        build=SimpleNamespace(),
        generate=lambda pressure: SimpleNamespace(),
        evaluate_candidate=evaluate_candidate,
        resource=ResourceType.MAGICKA,
        maximum_amount=30_000,
        trigger_fraction=0.25,
        restoration_resolver=lambda action: None,
        max_iterations=4,
    )

    assert result.converged is True
    assert stabilization.observed_state == ("hard:candidate-a",)
    assert len(evaluations) == 1
    assert hard_state.results[0].candidate_id == "candidate-a"
    assert stabilization.kwargs["resource"] is ResourceType.MAGICKA
    assert stabilization.kwargs["maximum_amount"] == 30_000
    assert stabilization.kwargs["trigger_fraction"] == 0.25
    assert stabilization.kwargs["max_iterations"] == 4
