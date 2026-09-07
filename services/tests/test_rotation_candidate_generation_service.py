from types import SimpleNamespace

import pytest

from minmax.demand_anticipatory_duration_scheduler import DemandRefreshLead
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_generation_service import (
    RotationCandidateGenerationService,
    RotationRefreshLeadCandidateOption,
)


class _RefinementService:
    def __init__(self):
        self.calls = []

    def refine(
        self,
        plan,
        *,
        priorities=None,
        wait_decision=None,
        demands=(),
        demand_refresh_leads=(),
    ):
        self.calls.append(
            {
                "plan": plan,
                "priorities": priorities,
                "wait_decision": wait_decision,
                "demands": tuple(demands),
                "leads": tuple(demand_refresh_leads),
            }
        )
        return SimpleNamespace(plan=plan)


def _seed() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=(),
    )


def _lead(skill: str, seconds: float, *, demand: str = "Phase 2", bar: str = "front"):
    return DemandRefreshLead(
        demand_name=demand,
        bar=bar,
        skill_name=skill,
        lead_seconds=seconds,
    )


def test_generates_baseline_then_explicit_variants_through_same_refinement_path() -> None:
    refinement = _RefinementService()
    service = RotationCandidateGenerationService(refinement)
    priorities = object()
    demands = (object(),)
    wait_decision = object()

    result = service.generate(
        seed_plan=_seed(),
        priorities=priorities,
        demands=demands,
        wait_decision=wait_decision,
        options=(
            RotationRefreshLeadCandidateOption(
                option_id="phase2-seeds-3s",
                refresh_leads=(_lead("Budding Seeds", 3.0),),
            ),
            RotationRefreshLeadCandidateOption(
                option_id="phase2-two-leads",
                refresh_leads=(
                    _lead("Combat Prayer", 1.0),
                    _lead("Budding Seeds", 2.0),
                ),
            ),
        ),
    )

    assert [candidate.candidate_id for candidate in result] == [
        "baseline",
        "phase2-seeds-3s",
        "phase2-two-leads",
    ]
    assert refinement.calls[0]["leads"] == ()
    assert refinement.calls[1]["leads"] == (_lead("Budding Seeds", 3.0),)
    assert refinement.calls[2]["leads"] == (
        _lead("Budding Seeds", 2.0),
        _lead("Combat Prayer", 1.0),
    )
    assert all(call["priorities"] is priorities for call in refinement.calls)
    assert all(call["demands"] == demands for call in refinement.calls)
    assert all(call["wait_decision"] is wait_decision for call in refinement.calls)


def test_semantic_duplicates_and_empty_baseline_equivalent_options_are_removed() -> None:
    refinement = _RefinementService()
    service = RotationCandidateGenerationService(refinement)
    seeds = _lead("Budding Seeds", 3.0)
    prayer = _lead("Combat Prayer", 1.0)

    result = service.generate(
        seed_plan=_seed(),
        priorities=object(),
        demands=(object(),),
        options=(
            RotationRefreshLeadCandidateOption(option_id="empty", refresh_leads=()),
            RotationRefreshLeadCandidateOption(
                option_id="first",
                refresh_leads=(prayer, seeds),
            ),
            RotationRefreshLeadCandidateOption(
                option_id="same-policy-different-name",
                refresh_leads=(seeds, prayer),
            ),
        ),
    )

    assert [candidate.candidate_id for candidate in result] == ["baseline", "first"]
    assert len(refinement.calls) == 2


def test_duplicate_refresh_target_inside_one_candidate_fails_explicitly() -> None:
    service = RotationCandidateGenerationService(_RefinementService())

    with pytest.raises(ValueError, match="duplicate refresh-lead target"):
        service.generate(
            seed_plan=_seed(),
            priorities=object(),
            demands=(object(),),
            options=(
                RotationRefreshLeadCandidateOption(
                    option_id="conflicting",
                    refresh_leads=(
                        _lead("Budding Seeds", 2.0),
                        _lead("Budding Seeds", 3.0),
                    ),
                ),
            ),
        )


def test_duplicate_candidate_ids_for_distinct_policies_fail_explicitly() -> None:
    service = RotationCandidateGenerationService(_RefinementService())

    with pytest.raises(ValueError, match="duplicate rotation candidate id"):
        service.generate(
            seed_plan=_seed(),
            priorities=object(),
            demands=(object(),),
            options=(
                RotationRefreshLeadCandidateOption(
                    option_id="aware",
                    refresh_leads=(_lead("Budding Seeds", 2.0),),
                ),
                RotationRefreshLeadCandidateOption(
                    option_id="AWARE",
                    refresh_leads=(_lead("Budding Seeds", 3.0),),
                ),
            ),
        )


def test_candidate_family_limit_fails_instead_of_silently_truncating() -> None:
    service = RotationCandidateGenerationService(
        _RefinementService(),
        max_candidates=2,
    )

    with pytest.raises(ValueError, match="exceeds explicit limit: 3 > 2"):
        service.generate(
            seed_plan=_seed(),
            priorities=object(),
            demands=(object(),),
            options=(
                RotationRefreshLeadCandidateOption(
                    option_id="two-seconds",
                    refresh_leads=(_lead("Budding Seeds", 2.0),),
                ),
                RotationRefreshLeadCandidateOption(
                    option_id="three-seconds",
                    refresh_leads=(_lead("Budding Seeds", 3.0),),
                ),
            ),
        )
