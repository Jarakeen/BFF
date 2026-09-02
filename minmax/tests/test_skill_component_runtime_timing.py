import pytest

from minmax.runtime_event import schedule_periodic_runtime_events
from minmax.skill_component_runtime_timing import (
    RuntimeCadenceBoundKind,
    extract_skill_component_runtime_timing,
)


def test_charged_atronach_keeps_interval_but_requires_parent_active_window():
    timing = extract_skill_component_runtime_timing(
        "The atronach calls upon a lightning storm every 2 seconds, dealing $2 Shock Damage."
    )
    assert timing is not None
    assert timing.interval_seconds == 2.0
    assert timing.bound_kind is RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW
    assert timing.occurrence_count is None
    assert timing.duration_seconds is None


def test_pack_leader_once_every_is_cadence_not_cooldown_semantics():
    timing = extract_skill_component_runtime_timing(
        "You summon two direwolves that deal $1 Physical Damage twice or $2 Physical Damage once every 2 seconds."
    )
    assert timing is not None
    assert timing.interval_seconds == 2.0
    assert timing.bound_kind is RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW


def test_budding_seeds_preserves_explicit_state_window():
    timing = extract_skill_component_runtime_timing(
        "While the field grows, you and allies are healed for $2 Health every 1 second."
    )
    assert timing is not None
    assert timing.interval_seconds == 1.0
    assert timing.bound_kind is RuntimeCadenceBoundKind.EXPLICIT_STATE_WINDOW


def test_bound_armaments_uses_runtime_stack_count_with_explicit_cap():
    timing = extract_skill_component_runtime_timing(
        "When at one or more stacks, you can arm up to 4 of them to strike your target "
        "for $1 Physical Damage every 0.3 seconds for each stack of Bound Armaments consumed."
    )
    assert timing is not None
    assert timing.interval_seconds == 0.3
    assert timing.bound_kind is RuntimeCadenceBoundKind.STACK_COUNT
    assert timing.max_occurrence_count == 4

    schedule = timing.to_periodic_schedule(
        trigger="bound_armaments_strike",
        source="Bound Armaments",
        first_occurrence_time_seconds=5.0,
        stack_count=3,
    )
    events = schedule_periodic_runtime_events(schedule)
    assert [event.time_seconds for event in events] == [5.0, 5.3, 5.6]


def test_bound_armaments_caps_runtime_stack_count_at_four():
    timing = extract_skill_component_runtime_timing(
        "When at one or more stacks, you can arm up to 4 of them to strike your target "
        "for $1 Physical Damage every 0.3 seconds for each stack of Bound Armaments consumed."
    )
    assert timing is not None
    schedule = timing.to_periodic_schedule(
        trigger="bound_armaments_strike",
        source="Bound Armaments",
        first_occurrence_time_seconds=1.0,
        stack_count=9,
    )
    assert schedule.occurrence_count == 4


def test_frozen_colossus_preserves_count_and_duration_without_inventing_interval():
    timing = extract_skill_component_runtime_timing(
        "The Colossus smashes the ground three times over 3 seconds, dealing $1 Frost Damage with each smash."
    )
    assert timing is not None
    assert timing.bound_kind is RuntimeCadenceBoundKind.FIXED_COUNT_DURATION
    assert timing.occurrence_count == 3
    assert timing.duration_seconds == 3.0
    assert timing.interval_seconds is None


def test_fixed_count_duration_requires_verified_interval_before_scheduling():
    timing = extract_skill_component_runtime_timing(
        "The Colossus smashes the ground three times over 3 seconds, dealing $1 Frost Damage with each smash."
    )
    assert timing is not None
    with pytest.raises(ValueError, match="verified positive interval"):
        timing.to_periodic_schedule(
            trigger="colossus_smash",
            source="Frozen Colossus",
            first_occurrence_time_seconds=1.0,
        )


def test_fixed_count_duration_can_schedule_when_verified_interval_is_supplied():
    timing = extract_skill_component_runtime_timing(
        "The Colossus smashes the ground three times over 3 seconds, dealing $1 Frost Damage with each smash."
    )
    assert timing is not None
    schedule = timing.to_periodic_schedule(
        trigger="colossus_smash",
        source="Frozen Colossus",
        first_occurrence_time_seconds=1.0,
        interval_seconds=1.0,
    )
    events = schedule_periodic_runtime_events(schedule)
    assert [event.time_seconds for event in events] == [1.0, 2.0, 3.0]


def test_active_window_cadence_refuses_to_invent_parent_duration():
    timing = extract_skill_component_runtime_timing(
        "The atronach calls upon a lightning storm every 2 seconds, dealing $2 Shock Damage."
    )
    assert timing is not None
    with pytest.raises(ValueError, match="active_end_time_seconds"):
        timing.to_periodic_schedule(
            trigger="atronach_storm",
            source="Summon Charged Atronach",
            first_occurrence_time_seconds=2.0,
        )


def test_active_window_cadence_schedules_only_inside_caller_window():
    timing = extract_skill_component_runtime_timing(
        "While the field grows, you and allies are healed for $2 Health every 1 second."
    )
    assert timing is not None
    schedule = timing.to_periodic_schedule(
        trigger="budding_seeds_heal",
        source="Budding Seeds",
        first_occurrence_time_seconds=1.0,
        active_end_time_seconds=3.5,
    )
    events = schedule_periodic_runtime_events(schedule)
    assert [event.time_seconds for event in events] == [1.0, 2.0, 3.0]


def test_non_recurring_component_has_no_runtime_timing():
    assert extract_skill_component_runtime_timing("Deal $1 Flame Damage to an enemy.") is None
