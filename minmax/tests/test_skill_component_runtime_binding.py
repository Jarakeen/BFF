from minmax.skill_component_runtime_binding import (
    RuntimeScheduleBindingResult,
    SkillComponentRuntimeState,
    bind_skill_component_runtime_schedule,
    required_runtime_inputs,
    schedule_skill_component_runtime_events,
)
from minmax.skill_component_runtime_timing import extract_skill_component_runtime_timing


def _timing(text: str):
    timing = extract_skill_component_runtime_timing(text)
    assert timing is not None
    return timing


def test_atronach_requires_first_occurrence_and_active_window():
    timing = _timing(
        "The atronach calls upon a lightning storm every 2 seconds, dealing $2 Shock Damage."
    )
    assert required_runtime_inputs(timing) == (
        "first_occurrence_time_seconds",
        "active_end_time_seconds",
    )

    result = bind_skill_component_runtime_schedule(
        timing,
        SkillComponentRuntimeState(),
        trigger="charged_atronach_storm",
        source="Summon Charged Atronach",
    )
    assert result.schedule is None
    assert result.unresolved == (
        "first_occurrence_time_seconds",
        "active_end_time_seconds",
    )


def test_atronach_binds_to_caller_active_window_without_inferring_duration():
    timing = _timing(
        "The atronach calls upon a lightning storm every 2 seconds, dealing $2 Shock Damage."
    )
    result = bind_skill_component_runtime_schedule(
        timing,
        SkillComponentRuntimeState(
            first_occurrence_time_seconds=2.0,
            active_end_time_seconds=8.0,
        ),
        trigger="charged_atronach_storm",
        source="Summon Charged Atronach",
    )
    assert result.resolved
    assert result.schedule is not None
    assert result.schedule.interval_seconds == 2.0
    assert result.schedule.start_time_seconds == 2.0
    assert result.schedule.end_time_seconds == 8.0
    assert result.schedule.occurrence_count is None


def test_budding_seeds_requires_explicit_state_window_end():
    timing = _timing(
        "While the field grows, you and allies are healed for $2 Health every 1 second."
    )
    result = bind_skill_component_runtime_schedule(
        timing,
        SkillComponentRuntimeState(first_occurrence_time_seconds=1.0),
        trigger="budding_seeds_tick",
        source="Budding Seeds",
    )
    assert result.unresolved == ("active_end_time_seconds",)


def test_bound_armaments_uses_runtime_stack_count_capped_by_source_maximum():
    timing = _timing(
        "When at one or more stacks, you can arm up to 4 of them to strike your target for "
        "$1 Physical Damage every 0.3 seconds for each stack of Bound Armaments consumed."
    )
    events = schedule_skill_component_runtime_events(
        timing,
        SkillComponentRuntimeState(
            first_occurrence_time_seconds=10.0,
            stack_count=9,
        ),
        trigger="bound_armaments_strike",
        source="Bound Armaments",
        starting_sequence=4,
    )
    assert not isinstance(events, RuntimeScheduleBindingResult)
    assert [event.time_seconds for event in events] == [10.0, 10.3, 10.6, 10.9]
    assert [event.sequence for event in events] == [4, 5, 6, 7]


def test_zero_stack_count_remains_explicitly_unresolved():
    timing = _timing(
        "When at one or more stacks, you can arm up to 4 of them to strike your target for "
        "$1 Physical Damage every 0.3 seconds for each stack of Bound Armaments consumed."
    )
    result = bind_skill_component_runtime_schedule(
        timing,
        SkillComponentRuntimeState(
            first_occurrence_time_seconds=10.0,
            stack_count=0,
        ),
        trigger="bound_armaments_strike",
        source="Bound Armaments",
    )
    assert result.schedule is None
    assert result.unresolved == ("stack_count",)


def test_frozen_colossus_requires_verified_within_window_interval():
    timing = _timing(
        "The Colossus smashes the ground three times over 3 seconds, dealing $1 Frost Damage."
    )
    assert required_runtime_inputs(timing) == (
        "first_occurrence_time_seconds",
        "verified_interval_seconds",
    )
    result = bind_skill_component_runtime_schedule(
        timing,
        SkillComponentRuntimeState(first_occurrence_time_seconds=0.0),
        trigger="frozen_colossus_smash",
        source="Frozen Colossus",
    )
    assert result.unresolved == ("verified_interval_seconds",)


def test_frozen_colossus_uses_verified_interval_and_preserves_count_duration_bounds():
    timing = _timing(
        "The Colossus smashes the ground three times over 3 seconds, dealing $1 Frost Damage."
    )
    events = schedule_skill_component_runtime_events(
        timing,
        SkillComponentRuntimeState(
            first_occurrence_time_seconds=0.5,
            verified_interval_seconds=1.0,
        ),
        trigger="frozen_colossus_smash",
        source="Frozen Colossus",
    )
    assert not isinstance(events, RuntimeScheduleBindingResult)
    assert [event.time_seconds for event in events] == [0.5, 1.5, 2.5]


def test_invalid_state_window_order_is_rejected():
    try:
        SkillComponentRuntimeState(
            first_occurrence_time_seconds=5.0,
            active_end_time_seconds=4.0,
        )
    except ValueError as exc:
        assert "cannot precede" in str(exc)
    else:
        raise AssertionError("expected invalid window ordering to fail")
