from types import SimpleNamespace

import pytest

from minmax.demand_anticipatory_duration_scheduler import DemandRefreshLead
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_generation_service import (
    RotationCandidateGenerationService,
    RotationRefreshLeadCandidateOption,
)


class _RefinementService:
    def __init__(self) -> None:
        self.wait_decisions = []

    def refine(
        self,
        plan,
        *,
        priorities=None,
        wait_decision=None,
        demands=(),
        demand_refresh_leads=(),
    ):
        self.wait_decisions.append(wait_decision)
        if wait_decision is not None:
            wait_decision["used"] += 1
        return SimpleNamespace(plan=plan)


def _seed() -> RotationPlan:
    return RotationPlan(
        character_name="Rotation Test",
        build_name="Role Neutral",
        duration_seconds=20.0,
        actions=(),
    )


def _lead(seconds: float) -> DemandRefreshLead:
    return DemandRefreshLead(
        demand_name="Mechanic",
        bar="front",
        skill_name="Required Skill",
        lead_seconds=seconds,
    )


def test_wait_decision_factory_supplies_fresh_state_per_candidate() -> None:
    refinement = _RefinementService()
    service = RotationCandidateGenerationService(refinement)
    created = []

    def factory():
        state = {"used": 0}
        created.append(state)
        return state

    result = service.generate(
        seed_plan=_seed(),
        priorities=object(),
        wait_decision_factory=factory,
        options=(
            RotationRefreshLeadCandidateOption(
                option_id="lead-2s",
                refresh_leads=(_lead(2.0),),
            ),
            RotationRefreshLeadCandidateOption(
                option_id="lead-3s",
                refresh_leads=(_lead(3.0),),
            ),
        ),
    )

    assert [candidate.candidate_id for candidate in result] == [
        "baseline",
        "lead-2s",
        "lead-3s",
    ]
    assert len(created) == 3
    assert len({id(item) for item in refinement.wait_decisions}) == 3
    assert [item["used"] for item in created] == [1, 1, 1]


def test_wait_decision_and_factory_cannot_be_supplied_together() -> None:
    service = RotationCandidateGenerationService(_RefinementService())

    with pytest.raises(ValueError, match="either wait_decision or wait_decision_factory"):
        service.generate(
            seed_plan=_seed(),
            priorities=object(),
            wait_decision=object(),
            wait_decision_factory=lambda: object(),
        )
