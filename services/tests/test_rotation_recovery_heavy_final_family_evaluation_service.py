from types import SimpleNamespace

import pytest

from minmax.rotation_plan import RotationPlan
from services.rotation_recovery_heavy_final_family_evaluation_service import (
    RotationRecoveryHeavyFinalFamilyEvaluationService,
)


def _snapshot(candidate_id: str):
    return SimpleNamespace(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Rotation Test",
            build_name=candidate_id,
            duration_seconds=20.0,
            actions=(),
        ),
    )


class _FakeBaseRanker:
    def __init__(self) -> None:
        self.received = ()

    def rank(self, candidates):
        self.received = tuple(candidates)
        return tuple(
            SimpleNamespace(
                candidate_id=item.candidate_id,
                tier=SimpleNamespace(value="eligible"),
                rank=index + 1,
                reasons=(),
            )
            for index, item in enumerate(reversed(self.received))
        )


class _FakeEffectUptimeService:
    def __init__(self) -> None:
        self.calls = []

    def assess(self, *, plan, build, requirements, passives=()):
        self.calls.append(
            {
                "plan": plan,
                "build": build,
                "requirements": tuple(requirements),
                "passives": tuple(passives),
            }
        )
        return (f"assessment:{plan.build_name}",)


class _FakeEffectRanker:
    def __init__(self) -> None:
        self.received = ()

    def rank(self, candidates):
        self.received = tuple(candidates)
        return tuple(
            SimpleNamespace(
                candidate_id=item.ranking_input.candidate_id,
                tier=SimpleNamespace(value="eligible"),
                rank=index + 1,
                reasons=(),
            )
            for index, item in enumerate(self.received)
        )


def test_generic_evaluator_rebuilds_scorecards_from_final_stabilized_family() -> None:
    ranker = _FakeBaseRanker()
    service = RotationRecoveryHeavyFinalFamilyEvaluationService(base_ranker=ranker)
    snapshots = (_snapshot("alpha"), _snapshot("beta"))
    resolved = []

    def resolve(snapshot):
        resolved.append((snapshot.candidate_id, snapshot.plan.build_name))
        return SimpleNamespace(marker=f"scorecard:{snapshot.candidate_id}")

    evaluator = service.generic_evaluator(scorecard_resolver=resolve)
    ranked = evaluator(snapshots)

    assert resolved == [("alpha", "alpha"), ("beta", "beta")]
    assert [item.candidate_id for item in ranker.received] == ["alpha", "beta"]
    assert ranker.received[0].scorecard.marker == "scorecard:alpha"
    assert ranker.received[1].scorecard.marker == "scorecard:beta"
    assert [item.candidate_id for item in ranked] == ["beta", "alpha"]


def test_effect_evaluator_reassesses_final_plans_and_forwards_passives() -> None:
    uptime = _FakeEffectUptimeService()
    effect_ranker = _FakeEffectRanker()
    service = RotationRecoveryHeavyFinalFamilyEvaluationService(
        effect_uptime_service=uptime,
        effect_ranker=effect_ranker,
    )
    snapshots = (_snapshot("healer"), _snapshot("tank"))
    build = SimpleNamespace(name="build-aware")
    requirements = (SimpleNamespace(effect_name="Major Brittle"),)
    passives = (SimpleNamespace(source="Serpent's Disdain"),)

    evaluator = service.effect_evaluator(
        build=build,
        scorecard_resolver=lambda snapshot: SimpleNamespace(
            marker=f"scorecard:{snapshot.candidate_id}"
        ),
        requirements=requirements,
        passives=passives,
    )
    ranked = evaluator(snapshots)

    assert [call["plan"].build_name for call in uptime.calls] == ["healer", "tank"]
    assert all(call["build"] is build for call in uptime.calls)
    assert all(call["requirements"] == requirements for call in uptime.calls)
    assert all(call["passives"] == passives for call in uptime.calls)
    assert effect_ranker.received[0].effect_uptime_assessments == (
        "assessment:healer",
    )
    assert effect_ranker.received[1].effect_uptime_assessments == (
        "assessment:tank",
    )
    assert [item.candidate_id for item in ranked] == ["healer", "tank"]


def test_final_family_adapter_rejects_ranker_candidate_set_drift() -> None:
    class _DroppingRanker:
        def rank(self, candidates):
            return (
                SimpleNamespace(
                    candidate_id=candidates[0].candidate_id,
                    tier=SimpleNamespace(value="eligible"),
                    rank=1,
                    reasons=(),
                ),
            )

    service = RotationRecoveryHeavyFinalFamilyEvaluationService(
        base_ranker=_DroppingRanker()
    )

    with pytest.raises(
        ValueError,
        match="final stabilized family ranking did not return the same candidate set",
    ):
        service.evaluate_generic(
            (_snapshot("alpha"), _snapshot("beta")),
            scorecard_resolver=lambda snapshot: SimpleNamespace(
                marker=snapshot.candidate_id
            ),
        )
