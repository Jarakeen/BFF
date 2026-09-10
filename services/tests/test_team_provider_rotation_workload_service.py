from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.team_provider_rotation_workload_service import (
    TeamProviderRotationContribution,
    TeamProviderRotationWorkloadService,
    TeamProviderScheduledActionCost,
)


def _plan(character, build, *actions, unresolved=()):
    return RotationPlan(
        character_name=character,
        build_name=build,
        duration_seconds=60.0,
        actions=tuple(actions),
        unresolved=unresolved,
    )


def _action_cost(
    time_seconds,
    sequence,
    *,
    gcd=1.0,
    cast_channel=0.0,
    resource_costs=None,
    ultimate_cost=None,
    displacement=0.0,
    heavy_completed=None,
):
    return TeamProviderScheduledActionCost(
        time_seconds=time_seconds,
        sequence=sequence,
        gcd_seconds=gcd,
        cast_channel_seconds=cast_channel,
        resource_costs=resource_costs,
        ultimate_cost=ultimate_cost,
        primary_role_displacement_seconds=displacement,
        heavy_attack_completed=heavy_completed,
    )


def test_assesses_multi_carrier_workload_without_weighting_unlike_dimensions():
    tank = _plan(
        "Tank",
        "Horn Tank",
        RotationAction(0.0, 0, RotationActionKind.ULTIMATE, "Aggressive Horn", "front"),
        RotationAction(1.0, 0, RotationActionKind.BAR_SWAP, None, "back"),
        RotationAction(2.0, 0, RotationActionKind.HEAVY_ATTACK, None, "back"),
    )
    healer = _plan(
        "Healer",
        "Horn Healer",
        RotationAction(30.0, 0, RotationActionKind.ULTIMATE, "Aggressive Horn", "back"),
        RotationAction(31.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
    )

    workload = TeamProviderRotationWorkloadService().assess(
        alternative_id="alternating tank + healer horns",
        effect_key="Major Force",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(
            TeamProviderRotationContribution(
                plan=tank,
                provider_actions=(_action_cost(0.0, 0, ultimate_cost=250),),
            ),
            TeamProviderRotationContribution(
                plan=healer,
                provider_actions=(
                    _action_cost(30.0, 0, ultimate_cost=250, displacement=1.0),
                ),
            ),
        ),
    )

    assert workload.viable
    assert workload.effect_key == "major_force"
    assert workload.contributor_count == 2
    assert workload.provider_applications == 2
    assert workload.provider_applications_per_minute == 2.0
    assert workload.provider_refreshes == 0
    assert workload.provider_gcd_seconds == 2.0
    assert workload.provider_cast_channel_seconds == 0.0
    assert workload.refreshes_per_minute == 0.0
    assert workload.resource_costs == ()
    assert workload.ultimate_spent == 500.0
    assert workload.occupied_bar_slot_count == 2
    assert workload.primary_role_displacement_seconds == 1.0
    assert workload.whole_plan_burden.ultimate_casts == 2
    assert workload.whole_plan_burden.heavy_attacks == 1


def test_compare_exposes_tradeoffs_for_two_resolved_coverage_plans():
    service = TeamProviderRotationWorkloadService()
    baseline_plan = _plan(
        "Healer",
        "Skill Provider",
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Provider Skill", "front"),
        RotationAction(20.0, 0, RotationActionKind.SKILL, "Provider Skill", "front"),
        RotationAction(40.0, 0, RotationActionKind.SKILL, "Provider Skill", "front"),
    )
    candidate_plan = _plan(
        "Tank",
        "Ultimate Provider",
        RotationAction(0.0, 0, RotationActionKind.ULTIMATE, "Provider Ultimate", "back"),
        RotationAction(1.0, 0, RotationActionKind.HEAVY_ATTACK, None, "back"),
    )
    baseline = service.assess(
        alternative_id="three skill refreshes",
        effect_key="major vulnerability",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(
            TeamProviderRotationContribution(
                plan=baseline_plan,
                provider_actions=tuple(
                    _action_cost(
                        time,
                        0,
                        resource_costs=(("magicka", 2700),),
                        displacement=1.0,
                    )
                    for time in (0.0, 20.0, 40.0)
                ),
            ),
        ),
    )
    candidate = service.assess(
        alternative_id="one ultimate",
        effect_key="major_vulnerability",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(
            TeamProviderRotationContribution(
                plan=candidate_plan,
                provider_actions=(_action_cost(0.0, 0, ultimate_cost=200),),
            ),
        ),
    )

    comparison = service.compare(baseline, candidate)

    assert comparison.provider_applications_delta == -2
    assert comparison.provider_applications_per_minute_delta == -2.0
    assert comparison.provider_refreshes_delta == -2
    assert comparison.provider_gcd_seconds_delta == -2.0
    assert comparison.provider_cast_channel_seconds_delta == 0.0
    assert comparison.refreshes_per_minute_delta == -2.0
    assert comparison.resource_cost_deltas == (("magicka", -8100.0),)
    assert comparison.ultimate_spent_delta == 200.0
    assert comparison.occupied_bar_slot_count_delta == 0
    assert comparison.primary_role_displacement_seconds_delta == -3.0
    assert comparison.skill_casts_delta == -3
    assert comparison.ultimate_casts_delta == 1
    assert comparison.heavy_attacks_delta == 1


def test_unresolved_cost_evidence_blocks_workload_comparison():
    plan = _plan(
        "Magrat",
        "DF Healer",
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Provider Skill", "front"),
    )
    unresolved = TeamProviderRotationWorkloadService().assess(
        alternative_id="unknown cost",
        effect_key="minor courage",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(
            TeamProviderRotationContribution(
                plan=plan,
                provider_actions=(
                    _action_cost(0.0, 0, gcd=None, displacement=None),
                ),
            ),
        ),
    )

    assert not unresolved.viable
    assert any("unresolved GCD occupancy" in item for item in unresolved.unresolved)
    assert any(
        "unresolved primary-role displacement" in item
        for item in unresolved.unresolved
    )

    try:
        TeamProviderRotationWorkloadService.compare(unresolved, unresolved)
    except ValueError as exc:
        assert "coverage-satisfying, resolved" in str(exc)
    else:
        raise AssertionError("expected unresolved provider workloads to fail closed")


def test_coverage_failures_remain_hard_gates_before_workload_comparison():
    plan = _plan(
        "Tank",
        "Provider Tank",
        RotationAction(0.0, 0, RotationActionKind.ULTIMATE, "Provider Ultimate", "front"),
    )
    service = TeamProviderRotationWorkloadService()
    contribution = TeamProviderRotationContribution(
        plan=plan,
        provider_actions=(_action_cost(0.0, 0, ultimate_cost=200),),
    )
    partial = service.assess(
        alternative_id="cheap but partial",
        effect_key="major force",
        duration_seconds=60.0,
        recipient_coverage_met=False,
        temporal_coverage_met=True,
        contributions=(contribution,),
    )
    complete = service.assess(
        alternative_id="complete",
        effect_key="major force",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(contribution,),
    )

    assert not partial.viable
    try:
        service.compare(complete, partial)
    except ValueError as exc:
        assert "coverage-satisfying" in str(exc)
    else:
        raise AssertionError("expected partial coverage to block workload comparison")


def test_provider_evidence_must_bind_to_an_exact_supported_plan_action():
    plan = _plan(
        "Healer",
        "Provider Healer",
        RotationAction(0.0, 0, RotationActionKind.WAIT, None, "front"),
    )
    workload = TeamProviderRotationWorkloadService().assess(
        alternative_id="bad binding",
        effect_key="minor courage",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(
            TeamProviderRotationContribution(
                plan=plan,
                provider_actions=(
                    _action_cost(0.0, 0),
                    _action_cost(5.0, 0),
                ),
            ),
        ),
    )

    assert not workload.viable
    assert workload.provider_applications == 0
    assert any("not a supported provider cast" in item for item in workload.unresolved)
    assert any("is not in the rotation plan" in item for item in workload.unresolved)


def test_skill_provider_requires_explicit_resource_cost_evidence():
    plan = _plan(
        "Healer",
        "Provider Healer",
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Provider Skill", "front"),
    )
    workload = TeamProviderRotationWorkloadService().assess(
        alternative_id="unknown skill cost",
        effect_key="minor courage",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(
            TeamProviderRotationContribution(
                plan=plan,
                provider_actions=(_action_cost(0.0, 0),),
            ),
        ),
    )

    assert not workload.viable
    assert any("unresolved resource cost" in item for item in workload.unresolved)


def test_reviewed_free_skill_cost_is_explicit_not_assumed():
    plan = _plan(
        "Tank",
        "Free Provider",
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Free Provider Skill", "back"),
    )
    workload = TeamProviderRotationWorkloadService().assess(
        alternative_id="reviewed free skill",
        effect_key="minor courage",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(
            TeamProviderRotationContribution(
                plan=plan,
                provider_actions=(
                    _action_cost(0.0, 0, resource_costs=()),
                ),
            ),
        ),
    )

    assert workload.viable
    assert workload.resource_costs == ()


def test_fully_charged_heavy_attack_can_be_a_provider_application() -> None:
    plan = _plan(
        "Healer",
        "HA Provider",
        RotationAction(2.0, 0, RotationActionKind.HEAVY_ATTACK, None, "front"),
    )
    workload = TeamProviderRotationWorkloadService().assess(
        alternative_id="verified heavy provider",
        effect_key="major slayer",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(
            TeamProviderRotationContribution(
                plan=plan,
                provider_actions=(
                    _action_cost(
                        2.0,
                        0,
                        gcd=0.0,
                        cast_channel=1.8,
                        resource_costs=(),
                        displacement=1.8,
                        heavy_completed=True,
                    ),
                ),
            ),
        ),
    )

    assert workload.viable
    assert workload.provider_applications == 1
    assert workload.provider_gcd_seconds == 0.0
    assert workload.provider_cast_channel_seconds == 1.8
    assert workload.primary_role_displacement_seconds == 1.8
    assert workload.whole_plan_burden.heavy_attacks == 1


def test_heavy_attack_provider_requires_verified_completion_evidence() -> None:
    plan = _plan(
        "Healer",
        "HA Provider",
        RotationAction(2.0, 0, RotationActionKind.HEAVY_ATTACK, None, "front"),
    )
    workload = TeamProviderRotationWorkloadService().assess(
        alternative_id="unverified heavy provider",
        effect_key="major slayer",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(
            TeamProviderRotationContribution(
                plan=plan,
                provider_actions=(
                    _action_cost(
                        2.0,
                        0,
                        gcd=0.0,
                        cast_channel=1.8,
                        resource_costs=(),
                        displacement=1.8,
                    ),
                ),
            ),
        ),
    )

    assert not workload.viable
    assert workload.provider_applications == 0
    assert any(
        "verified fully charged completion evidence" in item
        for item in workload.unresolved
    )
