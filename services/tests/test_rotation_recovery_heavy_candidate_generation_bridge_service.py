from types import SimpleNamespace

import pytest

from minmax.demand_anticipatory_duration_scheduler import DemandRefreshLead
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_generation_service import (
    RotationCandidateGenerationService,
    RotationRefreshLeadCandidateOption,
)
from services.rotation_recovery_heavy_candidate_generation_bridge_service import (
    RotationRecoveryHeavyCandidateGenerationBridgeService,
)


class _GenerationService:
    def __init__(self, max_candidates=32):
        self.max_candidates = max_candidates
        self.calls = []

    _dedupe_options = staticmethod(RotationCandidateGenerationService._dedupe_options)

    def generate_policy(
        self,
        *,
        candidate_id,
        seed_plan,
        priorities,
        demands=(),
        refresh_leads=(),
        wait_decision=None,
        wait_decision_factory=None,
    ):
        provider = wait_decision_factory() if wait_decision_factory is not None else wait_decision
        self.calls.append(
            {
                "candidate_id": candidate_id,
                "seed_plan": seed_plan,
                "priorities": priorities,
                "demands": tuple(demands),
                "refresh_leads": tuple(refresh_leads),
                "provider": provider,
            }
        )
        return SimpleNamespace(candidate_id=candidate_id, plan=seed_plan)


def _seed() -> RotationPlan:
    return RotationPlan(
        character_name="Rotation Test",
        build_name="Role Neutral",
        duration_seconds=30.0,
        actions=(),
    )


def _lead(seconds: float) -> DemandRefreshLead:
    return DemandRefreshLead(
        demand_name="Phase 2",
        bar="front",
        skill_name="Support Skill",
        lead_seconds=seconds,
    )


def _evaluator(candidate_id):
    return lambda _plan, _replay: SimpleNamespace(candidate_id=candidate_id)


def test_bridge_builds_baseline_and_options_with_pressure_aware_fresh_providers() -> None:
    generation = _GenerationService()
    service = RotationRecoveryHeavyCandidateGenerationBridgeService(generation)
    pressures = []

    def wait_factory(candidate_id, pressure):
        value = object()
        pressures.append((candidate_id, pressure, value))
        return value

    result = service.build(
        seed_plan=_seed(),
        priorities=object(),
        evaluator_resolver=_evaluator,
        demands=(object(),),
        options=(
            RotationRefreshLeadCandidateOption(
                option_id="early-support",
                refresh_leads=(_lead(2.0),),
            ),
        ),
        wait_decision_factory=wait_factory,
    )

    assert [item.candidate_id for item in result.candidates] == [
        "baseline",
        "early-support",
    ]

    first_pressure = object()
    second_pressure = object()
    result.candidates[0].generate(first_pressure)
    result.candidates[0].generate(second_pressure)
    result.candidates[1].generate(first_pressure)

    assert [call["candidate_id"] for call in generation.calls] == [
        "baseline",
        "baseline",
        "early-support",
    ]
    assert generation.calls[0]["refresh_leads"] == ()
    assert generation.calls[2]["refresh_leads"] == (_lead(2.0),)
    assert pressures[0][0:2] == ("baseline", first_pressure)
    assert pressures[1][0:2] == ("baseline", second_pressure)
    assert pressures[2][0:2] == ("early-support", first_pressure)
    assert generation.calls[0]["provider"] is not generation.calls[1]["provider"]


def test_bridge_preserves_semantic_option_deduplication_and_candidate_identity() -> None:
    generation = _GenerationService()
    service = RotationRecoveryHeavyCandidateGenerationBridgeService(generation)

    result = service.build(
        seed_plan=_seed(),
        priorities=object(),
        evaluator_resolver=_evaluator,
        options=(
            RotationRefreshLeadCandidateOption(
                option_id="first",
                refresh_leads=(_lead(2.0),),
            ),
            RotationRefreshLeadCandidateOption(
                option_id="duplicate-policy",
                refresh_leads=(_lead(2.0),),
            ),
        ),
    )

    assert [item.candidate_id for item in result.candidates] == ["baseline", "first"]
    evaluation = result.candidates[1].evaluate_candidate(_seed(), object())
    assert evaluation.candidate_id == "first"


def test_bridge_rejects_duplicate_baseline_identity_and_family_overflow() -> None:
    service = RotationRecoveryHeavyCandidateGenerationBridgeService(_GenerationService())

    with pytest.raises(ValueError, match="duplicate recovery candidate generation id"):
        service.build(
            seed_plan=_seed(),
            priorities=object(),
            evaluator_resolver=_evaluator,
            baseline_id="baseline",
            options=(
                RotationRefreshLeadCandidateOption(
                    option_id="BASELINE",
                    refresh_leads=(_lead(1.0),),
                ),
            ),
        )

    limited = RotationRecoveryHeavyCandidateGenerationBridgeService(
        _GenerationService(max_candidates=1)
    )
    with pytest.raises(ValueError, match="exceeds explicit limit: 2 > 1"):
        limited.build(
            seed_plan=_seed(),
            priorities=object(),
            evaluator_resolver=_evaluator,
            options=(
                RotationRefreshLeadCandidateOption(
                    option_id="second",
                    refresh_leads=(_lead(1.0),),
                ),
            ),
        )
