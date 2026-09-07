from types import SimpleNamespace

from services.rotation_candidate_effect_obligation_service import (
    RotationEffectObligationRankingResult,
)
from services.rotation_candidate_hard_obligation_state_service import (
    RotationCandidateHardObligationStateService,
)
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingResult,
    RotationCandidateTier,
)


def _scorecard():
    demand_requirement = SimpleNamespace(
        demand_name="Portal prep",
        skill_name="Budding Seeds",
        bar="front",
        minimum_casts=1,
    )
    reserve_requirement = SimpleNamespace(
        demand_name="Portal prep",
        resource=SimpleNamespace(value="magicka"),
        minimum_amount=16_000,
    )
    reserve = SimpleNamespace(
        requirement=reserve_requirement,
        available_before_start=15_500,
        shortfall=500,
    )
    bar_violation = SimpleNamespace(
        window_name="Portal entry",
        time_seconds=30.0,
        action_kind=SimpleNamespace(value="skill"),
        action_name="Winter's Revenge",
        reason="back bar unavailable",
    )
    uptime_requirement = SimpleNamespace(
        skill_name="Combat Prayer",
        bar="front",
        minimum_uptime=0.8,
    )
    uptime = SimpleNamespace(
        requirement=uptime_requirement,
        observed_uptime=0.75,
        unresolved=(),
    )
    return SimpleNamespace(
        missing_demand_requirements=(demand_requirement,),
        missing_required_effects=("Major Courage",),
        failed_reserve_assessments=(reserve,),
        bar_availability_violations=(bar_violation,),
        failed_runtime_uptime_assessments=(uptime,),
        candidate_shortfall=125,
        candidate_specific_unresolved=("soft diagnostic changed",),
        inherited_unresolved=("shared limitation",),
        runtime_uptime_objective_assessment=SimpleNamespace(observed_uptime=0.99),
        consequence=SimpleNamespace(ending_resource_delta=9999),
    )


def test_scorecard_state_contains_only_canonical_hard_obligations() -> None:
    service = RotationCandidateHardObligationStateService()

    state = service.from_scorecard(_scorecard())

    assert state == tuple(sorted(state, key=str.casefold))
    assert any(item.startswith("demand|Portal prep|Budding Seeds|front|1") for item in state)
    assert "static_effect|Major Courage" in state
    assert "reserve|Portal prep|magicka|16000|15500|500" in state
    assert any(item.startswith("bar_legality|Portal entry|30|skill|Winter's Revenge") for item in state)
    assert "runtime_uptime|Combat Prayer|front|0.8|0.75" in state
    assert "resource_shortfall|125" in state

    combined = "\n".join(state)
    assert "soft diagnostic changed" not in combined
    assert "shared limitation" not in combined
    assert "0.99" not in combined
    assert "9999" not in combined


def test_effect_ranking_state_adds_only_failed_effect_obligations() -> None:
    base_scorecard = SimpleNamespace(
        missing_demand_requirements=(),
        missing_required_effects=(),
        failed_reserve_assessments=(),
        bar_availability_violations=(),
        failed_runtime_uptime_assessments=(),
        candidate_shortfall=0,
    )
    base = RotationCandidateRankingResult(
        candidate_id="candidate",
        scorecard=base_scorecard,
        tier=RotationCandidateTier.ELIGIBLE,
        rank=1,
        reasons=("soft reason that must not enter state",),
    )
    failed = SimpleNamespace(
        satisfied=False,
        requirement=SimpleNamespace(
            effect_name="Major Brittle",
            source_skill_name="Winter's Revenge",
            bar="back",
            minimum_uptime=0.9,
        ),
        observed_uptime=0.82,
        unresolved=(),
    )
    satisfied = SimpleNamespace(
        satisfied=True,
        requirement=SimpleNamespace(
            effect_name="Minor Toughness",
            source_skill_name="Enchanted Growth",
            bar="front",
            minimum_uptime=0.8,
        ),
        observed_uptime=0.95,
        unresolved=(),
    )
    result = RotationEffectObligationRankingResult(
        candidate_id="candidate",
        base_result=base,
        effect_uptime_assessments=(satisfied, failed),
        tier=RotationCandidateTier.INELIGIBLE,
        rank=1,
        reasons=("another presentation reason",),
    )

    state = RotationCandidateHardObligationStateService().from_effect_ranking_result(result)

    assert state == (
        "effect_uptime|Major Brittle|Winter's Revenge|back|0.9|0.82",
    )
    assert "Minor Toughness" not in "\n".join(state)
    assert "presentation reason" not in "\n".join(state)
