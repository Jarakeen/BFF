from __future__ import annotations

from services.rotation_execution_burden_service import RotationExecutionBurden
from services.team_provider_rotation_workload_service import TeamProviderRotationWorkload
from services.team_provider_workload_decision_service import (
    TeamProviderWorkloadDecision,
    TeamProviderWorkloadDecisionResult,
    TeamProviderWorkloadDecisionStatus,
)
from services.team_provider_workload_policy_service import (
    TeamProviderWorkloadPolicy,
    TeamProviderWorkloadPolicyDimension,
    TeamProviderWorkloadPolicyPriority,
    TeamProviderWorkloadPolicyService,
)


def _burden() -> RotationExecutionBurden:
    return RotationExecutionBurden(
        total_actions=10,
        skill_casts=10,
        ultimate_casts=0,
        light_attacks=0,
        heavy_attacks=0,
        potions=0,
        bar_swaps=0,
        waits=0,
    )


def _workload(
    alternative_id: str,
    *,
    effect_key: str = "major_slayer",
    duration_seconds: float = 60.0,
    applications: int = 3,
    gcd_seconds: float = 3.0,
    resource_costs: tuple[tuple[str, float], ...] = (("magicka", 3000.0),),
    ultimate_spent: float = 0.0,
    slots: tuple[str, ...] = ("magrat:front:provider",),
    displacement: float = 1.0,
) -> TeamProviderRotationWorkload:
    return TeamProviderRotationWorkload(
        alternative_id=alternative_id,
        effect_key=effect_key,
        duration_seconds=duration_seconds,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributor_count=1,
        provider_applications=applications,
        provider_applications_per_minute=applications * 60.0 / duration_seconds,
        provider_refreshes=max(0, applications - 1),
        provider_gcd_seconds=gcd_seconds,
        provider_cast_channel_seconds=0.0,
        refreshes_per_minute=max(0, applications - 1) * 60.0 / duration_seconds,
        resource_costs=resource_costs,
        ultimate_spent=ultimate_spent,
        occupied_bar_slots=slots,
        primary_role_displacement_seconds=displacement,
        whole_plan_burden=_burden(),
        unresolved=(),
    )


def _decision(
    workload: TeamProviderRotationWorkload,
    status: TeamProviderWorkloadDecisionStatus = TeamProviderWorkloadDecisionStatus.FRONTIER,
) -> TeamProviderWorkloadDecision:
    return TeamProviderWorkloadDecision(
        alternative_id=workload.alternative_id,
        effect_key=workload.effect_key,
        duration_seconds=workload.duration_seconds,
        status=status,
        workload=workload,
    )


def _result(*decisions: TeamProviderWorkloadDecision) -> TeamProviderWorkloadDecisionResult:
    return TeamProviderWorkloadDecisionResult(decisions=decisions)


def test_policy_applies_priorities_lexicographically_without_weighting():
    protects_role = _workload(
        "protects role",
        displacement=0.25,
        ultimate_spent=200.0,
        resource_costs=(("magicka", 5000.0),),
    )
    saves_ultimate = _workload(
        "saves ultimate",
        displacement=1.5,
        ultimate_spent=0.0,
        resource_costs=(("magicka", 1000.0),),
    )
    policy = TeamProviderWorkloadPolicy(
        policy_id="healer first",
        encounter_key="Sunspire Lokke HM",
        role_key="Healer",
        priorities=(
            TeamProviderWorkloadPolicyPriority(
                TeamProviderWorkloadPolicyDimension.PRIMARY_ROLE_DISPLACEMENT_SECONDS
            ),
            TeamProviderWorkloadPolicyPriority(
                TeamProviderWorkloadPolicyDimension.ULTIMATE_SPENT
            ),
        ),
    )

    selected = TeamProviderWorkloadPolicyService.select(
        _result(_decision(protects_role), _decision(saves_ultimate)),
        policy,
    )

    assert selected.preferred_ids == ("protects role",)
    assert selected.policy.encounter_key == "sunspire_lokke_hm"
    assert selected.policy.role_key == "healer"
    assert selected.selections[0].rationale == (
        "primary_role_displacement_seconds: kept protects role at 0.25; "
        "deprioritized saves ultimate=1.5",
    )


def test_later_priority_breaks_tie_left_by_earlier_priority():
    lower_magicka = _workload(
        "lower magicka",
        displacement=0.5,
        resource_costs=(("magicka", 1800.0),),
    )
    higher_magicka = _workload(
        "higher magicka",
        displacement=0.5,
        resource_costs=(("magicka", 4200.0),),
    )
    policy = TeamProviderWorkloadPolicy(
        policy_id="healer sustain",
        priorities=(
            TeamProviderWorkloadPolicyPriority(
                TeamProviderWorkloadPolicyDimension.PRIMARY_ROLE_DISPLACEMENT_SECONDS
            ),
            TeamProviderWorkloadPolicyPriority(
                TeamProviderWorkloadPolicyDimension.RESOURCE_SPEND,
                resource_type="Magicka",
            ),
        ),
    )

    selected = TeamProviderWorkloadPolicyService.select(
        _result(_decision(lower_magicka), _decision(higher_magicka)),
        policy,
    )

    assert selected.preferred_ids == ("lower magicka",)
    assert selected.selections[0].rationale == (
        "resource_spend:magicka: kept lower magicka at 1800; "
        "deprioritized higher magicka=4200",
    )


def test_policy_preserves_tied_frontier_survivors_when_priorities_do_not_separate_them():
    alpha = _workload("alpha", displacement=0.5, ultimate_spent=100.0)
    beta = _workload("beta", displacement=0.5, ultimate_spent=100.0)
    policy = TeamProviderWorkloadPolicy(
        policy_id="tie remains",
        priorities=(
            TeamProviderWorkloadPolicyPriority(
                TeamProviderWorkloadPolicyDimension.PRIMARY_ROLE_DISPLACEMENT_SECONDS
            ),
            TeamProviderWorkloadPolicyPriority(
                TeamProviderWorkloadPolicyDimension.ULTIMATE_SPENT
            ),
        ),
    )

    selected = TeamProviderWorkloadPolicyService.select(
        _result(_decision(alpha), _decision(beta)),
        policy,
    )

    assert selected.preferred_ids == ("alpha", "beta")
    assert selected.selections[0].rationale == ()


def test_policy_ignores_dominated_and_blocked_candidates_even_when_they_are_cheaper():
    frontier = _workload("frontier", displacement=1.0, ultimate_spent=100.0)
    dominated = _workload("dominated", displacement=0.0, ultimate_spent=0.0)
    blocked = _workload("blocked", displacement=0.0, ultimate_spent=0.0)
    policy = TeamProviderWorkloadPolicy(
        policy_id="frontier only",
        priorities=(
            TeamProviderWorkloadPolicyPriority(
                TeamProviderWorkloadPolicyDimension.PRIMARY_ROLE_DISPLACEMENT_SECONDS
            ),
        ),
    )

    selected = TeamProviderWorkloadPolicyService.select(
        _result(
            _decision(frontier),
            _decision(dominated, TeamProviderWorkloadDecisionStatus.DOMINATED),
            _decision(blocked, TeamProviderWorkloadDecisionStatus.BLOCKED),
        ),
        policy,
    )

    assert selected.preferred_ids == ("frontier",)
    assert selected.selections[0].considered_ids == ("frontier",)


def test_policy_selects_independently_inside_each_effect_and_duration_scope():
    short = _workload("short", effect_key="minor_berserk", duration_seconds=30.0)
    long = _workload("long", effect_key="minor_berserk", duration_seconds=60.0)
    slayer = _workload("slayer", effect_key="major_slayer", duration_seconds=60.0)
    policy = TeamProviderWorkloadPolicy(
        policy_id="scope safe",
        priorities=(
            TeamProviderWorkloadPolicyPriority(
                TeamProviderWorkloadPolicyDimension.PROVIDER_APPLICATIONS
            ),
        ),
    )

    selected = TeamProviderWorkloadPolicyService.select(
        _result(_decision(short), _decision(long), _decision(slayer)),
        policy,
    )

    assert tuple(
        (item.effect_key, item.duration_seconds, item.preferred_ids)
        for item in selected.selections
    ) == (
        ("major_slayer", 60.0, ("slayer",)),
        ("minor_berserk", 30.0, ("short",)),
        ("minor_berserk", 60.0, ("long",)),
    )


def test_resource_priority_requires_resource_type():
    try:
        TeamProviderWorkloadPolicyPriority(
            TeamProviderWorkloadPolicyDimension.RESOURCE_SPEND
        )
    except ValueError as exc:
        assert "requires resource_type" in str(exc)
    else:
        raise AssertionError("resource priority without resource_type should fail")


def test_non_resource_priority_rejects_resource_type():
    try:
        TeamProviderWorkloadPolicyPriority(
            TeamProviderWorkloadPolicyDimension.ULTIMATE_SPENT,
            resource_type="magicka",
        )
    except ValueError as exc:
        assert "only valid" in str(exc)
    else:
        raise AssertionError("non-resource priority with resource_type should fail")


def test_policy_rejects_duplicate_priorities():
    priority = TeamProviderWorkloadPolicyPriority(
        TeamProviderWorkloadPolicyDimension.ULTIMATE_SPENT
    )
    try:
        TeamProviderWorkloadPolicy(
            policy_id="duplicate",
            priorities=(priority, priority),
        )
    except ValueError as exc:
        assert "duplicate provider workload policy priority" in str(exc)
    else:
        raise AssertionError("duplicate policy priorities should fail")
