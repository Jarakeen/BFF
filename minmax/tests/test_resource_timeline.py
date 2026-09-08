from minmax.final_action_cost import calculate_final_action_cost
from minmax.recovery_timing import schedule_in_combat_recovery_ticks
from minmax.resource_costs import ResourceType, resolve_base_action_cost
from minmax.resource_state import StaticResourcePool
from minmax.resource_timeline import (
    ResourceCostEvent,
    ResourceMaximumEvent,
    ResourceTimelineEventKind,
    create_action_cost_events,
    run_resource_timeline,
)
from minmax.restoration_events import ResourceRestorationEvent


def _pool(resource: ResourceType = ResourceType.MAGICKA) -> StaticResourcePool:
    return StaticResourcePool(resource=resource, maximum=10000, displayed_recovery=1000)


def test_timeline_applies_cost_recovery_and_restore_in_time_order() -> None:
    pool = _pool()
    recovery = schedule_in_combat_recovery_ticks(pool, duration_seconds=4.0)
    result = run_resource_timeline(
        pool,
        starting_amount=8000,
        cost_events=(
            ResourceCostEvent(1.0, ResourceType.MAGICKA, 2000, "Skill A"),
            ResourceCostEvent(3.0, ResourceType.MAGICKA, 1500, "Skill B"),
        ),
        recovery_ticks=recovery,
        restoration_events=(
            ResourceRestorationEvent(3.5, ResourceType.MAGICKA, 500, "External restore"),
        ),
    )

    assert result.ending_amount == 7000
    assert result.ending_maximum == 10000
    assert [event.after for event in result.events] == [6000, 7000, 5500, 6000, 7000]
    assert [event.kind for event in result.events] == [
        ResourceTimelineEventKind.ACTION_COST,
        ResourceTimelineEventKind.RECOVERY_TICK,
        ResourceTimelineEventKind.ACTION_COST,
        ResourceTimelineEventKind.RESTORATION,
        ResourceTimelineEventKind.RECOVERY_TICK,
    ]


def test_same_timestamp_orders_cost_then_recovery_then_restoration() -> None:
    pool = _pool()
    recovery = schedule_in_combat_recovery_ticks(pool, duration_seconds=2.0)
    result = run_resource_timeline(
        pool,
        starting_amount=3000,
        cost_events=(ResourceCostEvent(2.0, ResourceType.MAGICKA, 2500, "Skill"),),
        recovery_ticks=recovery,
        restoration_events=(
            ResourceRestorationEvent(2.0, ResourceType.MAGICKA, 800, "Restore"),
        ),
    )

    assert [event.kind for event in result.events] == [
        ResourceTimelineEventKind.ACTION_COST,
        ResourceTimelineEventKind.RECOVERY_TICK,
        ResourceTimelineEventKind.RESTORATION,
    ]
    assert [event.after for event in result.events] == [500, 1500, 2300]


def test_resource_ceiling_change_clips_on_lowering_and_does_not_restore_on_raise() -> None:
    pool = _pool()
    result = run_resource_timeline(
        pool,
        starting_amount=9500,
        maximum_events=(
            ResourceMaximumEvent(1.0, ResourceType.MAGICKA, 9000, "Swap to back bar"),
            ResourceMaximumEvent(2.0, ResourceType.MAGICKA, 10000, "Swap to front bar"),
        ),
    )

    lower, raise_event = result.events
    assert lower.kind is ResourceTimelineEventKind.RESOURCE_MAXIMUM
    assert lower.before == 9500
    assert lower.after == 9000
    assert lower.maximum_before == 10000
    assert lower.maximum_after == 9000
    assert lower.clipped_amount == 500
    assert lower.applied_change == -500

    assert raise_event.before == 9000
    assert raise_event.after == 9000
    assert raise_event.maximum_before == 9000
    assert raise_event.maximum_after == 10000
    assert raise_event.clipped_amount == 0
    assert raise_event.applied_change == 0
    assert result.ending_amount == 9000
    assert result.ending_maximum == 10000


def test_resource_ceiling_change_precedes_same_timestamp_cost_recovery_and_restore() -> None:
    pool = _pool()
    recovery = schedule_in_combat_recovery_ticks(pool, duration_seconds=2.0)
    result = run_resource_timeline(
        pool,
        starting_amount=9500,
        maximum_events=(
            ResourceMaximumEvent(2.0, ResourceType.MAGICKA, 9000, "Swap to back bar"),
        ),
        cost_events=(ResourceCostEvent(2.0, ResourceType.MAGICKA, 1000, "Skill"),),
        recovery_ticks=recovery,
        restoration_events=(
            ResourceRestorationEvent(2.0, ResourceType.MAGICKA, 800, "Restore"),
        ),
    )

    assert [event.kind for event in result.events] == [
        ResourceTimelineEventKind.RESOURCE_MAXIMUM,
        ResourceTimelineEventKind.ACTION_COST,
        ResourceTimelineEventKind.RECOVERY_TICK,
        ResourceTimelineEventKind.RESTORATION,
    ]
    assert [event.after for event in result.events] == [9000, 8000, 9000, 9000]
    assert result.events[-1].wasted_restore == 800


def test_timeline_records_cost_shortfall_without_negative_resource() -> None:
    pool = _pool()
    result = run_resource_timeline(
        pool,
        starting_amount=1200,
        cost_events=(ResourceCostEvent(1.0, ResourceType.MAGICKA, 2000, "Too expensive"),),
    )

    event = result.events[0]
    assert result.ending_amount == 0
    assert result.has_shortfall
    assert result.total_shortfall == 800
    assert event.shortfall == 800
    assert event.attempted_change == -2000
    assert event.applied_change == -1200


def test_timeline_tracks_wasted_restoration_at_resource_cap() -> None:
    pool = _pool()
    result = run_resource_timeline(
        pool,
        starting_amount=9800,
        restoration_events=(
            ResourceRestorationEvent(1.0, ResourceType.MAGICKA, 1000, "Restore"),
        ),
    )

    event = result.events[0]
    assert result.ending_amount == 10000
    assert event.applied_change == 200
    assert event.wasted_restore == 800


def test_create_action_cost_events_preserves_compound_resource_costs() -> None:
    base = resolve_base_action_cost(
        ability_id=23819,
        base_cost=1148,
        base_mechanic=5,
        rank=4,
        morph=1,
    )
    final = calculate_final_action_cost(base)

    events = create_action_cost_events(
        time_seconds=1.0,
        final_cost=final,
        source="Molten Whip",
    )

    assert [(event.resource, event.amount) for event in events] == [
        (ResourceType.MAGICKA, 1148),
        (ResourceType.STAMINA, 1148),
    ]


def test_timeline_rejects_resource_mismatch_and_invalid_start() -> None:
    pool = _pool()

    try:
        run_resource_timeline(
            pool,
            starting_amount=5000,
            cost_events=(ResourceCostEvent(1.0, ResourceType.STAMINA, 1000, "Wrong pool"),),
        )
    except ValueError as exc:
        assert "does not match pool" in str(exc)
    else:
        raise AssertionError("Expected resource mismatch")

    try:
        run_resource_timeline(
            pool,
            starting_amount=5000,
            maximum_events=(
                ResourceMaximumEvent(1.0, ResourceType.STAMINA, 9000, "Wrong pool"),
            ),
        )
    except ValueError as exc:
        assert "does not match pool" in str(exc)
    else:
        raise AssertionError("Expected maximum-event resource mismatch")

    for invalid in (-1, 10001):
        try:
            run_resource_timeline(pool, starting_amount=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected invalid starting amount {invalid} to be rejected")
