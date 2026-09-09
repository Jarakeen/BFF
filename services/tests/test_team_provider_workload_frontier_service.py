import pytest

from services.rotation_execution_burden_service import RotationExecutionBurden
from services.team_provider_rotation_workload_service import TeamProviderRotationWorkload
from services.team_provider_workload_frontier_service import (
    TeamProviderWorkloadFrontierService,
)


def _burden(*, heavy_attacks=0, bar_swaps=0):
    return RotationExecutionBurden(
        total_actions=10 + heavy_attacks + bar_swaps,
        skill_casts=10,
        ultimate_casts=0,
        light_attacks=0,
        heavy_attacks=heavy_attacks,
        potions=0,
        bar_swaps=bar_swaps,
        waits=0,
    )


def _workload(
    alternative_id,
    *,
    applications=3,
    gcd_seconds=3.0,
    cast_seconds=0.0,
    resource_costs=(("magicka", 3000.0),),
    ultimate_spent=0.0,
    occupied_slots=("magrat:front:combat_prayer",),
    displacement=0.75,
    recipient_coverage_met=True,
    temporal_coverage_met=True,
    unresolved=(),
    effect_key="minor_berserk",
    duration_seconds=60.0,
    heavy_attacks=0,
    bar_swaps=0,
):
    return TeamProviderRotationWorkload(
        alternative_id=alternative_id,
        effect_key=effect_key,
        duration_seconds=duration_seconds,
        recipient_coverage_met=recipient_coverage_met,
        temporal_coverage_met=temporal_coverage_met,
        contributor_count=1,
        provider_applications=applications,
        provider_applications_per_minute=float(applications),
        provider_refreshes=max(0, applications - 1),
        provider_gcd_seconds=gcd_seconds,
        provider_cast_channel_seconds=cast_seconds,
        refreshes_per_minute=float(max(0, applications - 1)),
        resource_costs=resource_costs,
        ultimate_spent=ultimate_spent,
        occupied_bar_slots=occupied_slots,
        primary_role_displacement_seconds=displacement,
        whole_plan_burden=_burden(
            heavy_attacks=heavy_attacks,
            bar_swaps=bar_swaps,
        ),
        unresolved=unresolved,
    )


def test_removes_only_plan_that_is_no_better_in_any_provider_cost():
    efficient = _workload(
        "efficient",
        applications=2,
        gcd_seconds=2.0,
        resource_costs=(("magicka", 1800.0),),
        displacement=0.5,
    )
    expensive = _workload("expensive")

    result = TeamProviderWorkloadFrontierService.evaluate((efficient, expensive))

    assert result.frontier_ids == ("efficient",)
    assert tuple(item.alternative_id for item in result.dominated) == ("expensive",)
    assert result.blocked == ()
    relation = result.dominance[0]
    assert relation.preferred_id == "efficient"
    assert relation.dominated_id == "expensive"
    assert any("provider applications" in item for item in relation.improvements)
    assert any("magicka spend" in item for item in relation.improvements)


def test_preserves_genuine_tradeoff_instead_of_inventing_weighted_winner():
    fewer_casts = _workload(
        "fewer casts",
        applications=2,
        gcd_seconds=2.0,
        resource_costs=(("magicka", 5000.0),),
    )
    cheaper_casts = _workload(
        "cheaper casts",
        applications=3,
        gcd_seconds=3.0,
        resource_costs=(("magicka", 1800.0),),
    )

    result = TeamProviderWorkloadFrontierService.evaluate(
        (fewer_casts, cheaper_casts)
    )

    assert result.frontier_ids == ("fewer casts", "cheaper casts")
    assert result.dominated == ()
    assert result.dominance == ()


def test_blocked_plan_never_participates_in_frontier_dominance():
    viable = _workload("viable")
    blocked = _workload(
        "blocked",
        applications=1,
        gcd_seconds=1.0,
        resource_costs=(),
        displacement=0.0,
        temporal_coverage_met=False,
    )

    result = TeamProviderWorkloadFrontierService.evaluate((viable, blocked))

    assert result.frontier_ids == ("viable",)
    assert tuple(item.alternative_id for item in result.blocked) == ("blocked",)
    assert result.dominance == ()


def test_whole_plan_heavy_attack_count_is_not_assumed_to_be_universal_cost():
    no_heavy = _workload("no heavy", heavy_attacks=0)
    one_heavy = _workload("one heavy", heavy_attacks=1)

    result = TeamProviderWorkloadFrontierService.evaluate((no_heavy, one_heavy))

    assert result.frontier_ids == ("no heavy", "one heavy")
    assert result.dominance == ()


def test_free_provider_cost_dominates_same_plan_with_resource_spend():
    free = _workload("free", resource_costs=())
    costly = _workload("costly", resource_costs=(("magicka", 3000.0),))

    result = TeamProviderWorkloadFrontierService.evaluate((free, costly))

    assert result.frontier_ids == ("free",)
    assert result.dominance[0].improvements == ("magicka spend: 0 vs 3000",)


@pytest.mark.parametrize(
    "workloads, message",
    [
        (
            (_workload("a"), _workload("b", effect_key="major_slayer")),
            "one shared effect",
        ),
        (
            (_workload("a"), _workload("b", duration_seconds=90.0)),
            "one shared duration",
        ),
        (
            (_workload("same"), _workload("same")),
            "duplicate provider workload alternative_id",
        ),
    ],
)
def test_rejects_incomparable_or_ambiguous_frontier_input(workloads, message):
    with pytest.raises(ValueError, match=message):
        TeamProviderWorkloadFrontierService.evaluate(workloads)
