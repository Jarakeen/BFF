import pytest

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.runtime_event import (
    PeriodicRuntimeSchedule,
    RuntimeEvent,
    order_runtime_events,
    runtime_event_matches_component_trigger,
    runtime_event_matches_effect_variant,
    schedule_periodic_runtime_events,
)
from minmax.skill_component_trigger_relationship import (
    SkillComponentTriggerRelationship,
    SkillComponentTriggerType,
)


def test_runtime_event_preserves_phase6_trigger_identity():
    event = RuntimeEvent.for_skill_component_trigger(
        time_seconds=2.5,
        trigger_type=SkillComponentTriggerType.DAMAGE_DEALT,
        source="Static Reverberation",
    )
    relationship = SkillComponentTriggerRelationship(
        skill_rank_id=7779,
        coefficient_number=1,
        trigger_type=SkillComponentTriggerType.DAMAGE_DEALT,
        evidence="When you deal damage",
    )

    assert event.trigger == "damage_dealt"
    assert runtime_event_matches_component_trigger(event, relationship)


def test_runtime_event_does_not_match_different_phase6_trigger():
    event = RuntimeEvent.for_skill_component_trigger(
        time_seconds=0.0,
        trigger_type=SkillComponentTriggerType.LIGHT_ATTACK,
        source="Light Attack",
    )
    relationship = SkillComponentTriggerRelationship(
        skill_rank_id=1,
        coefficient_number=1,
        trigger_type=SkillComponentTriggerType.HEAVY_ATTACK,
        evidence="fully-charged Heavy Attack",
    )

    assert not runtime_event_matches_component_trigger(event, relationship)


def test_runtime_event_preserves_effect_variant_named_trigger():
    effect = EffectVariant(
        name="damage_shield",
        layer=EffectLayer.PROC,
        source="Champion Point: From the Brink",
        trigger="on_heal_target_below_25_percent_health",
    )
    event = RuntimeEvent.for_effect_variant(
        time_seconds=4.0,
        effect=effect,
        target="ally:1",
    )

    assert event.trigger == "on_heal_target_below_25_percent_health"
    assert event.source == effect.source
    assert event.target == "ally:1"
    assert runtime_event_matches_effect_variant(event, effect)


def test_ineligible_effect_variant_does_not_match_runtime_event():
    effect = EffectVariant(
        name="damage_shield",
        layer=EffectLayer.PROC,
        source="Champion Point: From the Brink",
        trigger="on_heal_target_below_25_percent_health",
        eligible=False,
    )
    event = RuntimeEvent(
        time_seconds=4.0,
        trigger="on_heal_target_below_25_percent_health",
        source="Combat event",
    )

    assert not runtime_event_matches_effect_variant(event, effect)


def test_runtime_event_requires_effect_variant_trigger():
    effect = EffectVariant(
        name="major_sorcery",
        layer=EffectLayer.CAST,
        source="Example Skill",
    )

    with pytest.raises(ValueError, match="does not define a runtime trigger"):
        RuntimeEvent.for_effect_variant(time_seconds=1.0, effect=effect)


def test_runtime_events_order_by_timestamp_then_sequence():
    later = RuntimeEvent(
        time_seconds=2.0,
        trigger="tick",
        source="later",
        sequence=0,
    )
    same_time_second = RuntimeEvent(
        time_seconds=1.0,
        trigger="tick",
        source="second",
        sequence=2,
    )
    same_time_first = RuntimeEvent(
        time_seconds=1.0,
        trigger="tick",
        source="first",
        sequence=1,
    )

    ordered = order_runtime_events((later, same_time_second, same_time_first))

    assert [event.source for event in ordered] == ["first", "second", "later"]


def test_periodic_schedule_uses_occurrence_count_without_float_accumulation():
    schedule = PeriodicRuntimeSchedule(
        trigger="component_tick",
        source="Bound Armaments",
        interval_seconds=0.3,
        start_time_seconds=0.3,
        occurrence_count=4,
    )

    events = schedule_periodic_runtime_events(schedule, starting_sequence=7)

    assert [event.time_seconds for event in events] == pytest.approx([0.3, 0.6, 0.9, 1.2])
    assert [event.sequence for event in events] == [7, 8, 9, 10]


def test_periodic_schedule_can_be_bounded_by_active_window():
    schedule = PeriodicRuntimeSchedule(
        trigger="component_tick",
        source="Budding Seeds",
        interval_seconds=1.0,
        start_time_seconds=1.0,
        end_time_seconds=4.0,
    )

    events = schedule_periodic_runtime_events(schedule)

    assert [event.time_seconds for event in events] == [1.0, 2.0, 3.0, 4.0]


def test_periodic_schedule_honors_first_bound_when_count_and_window_are_present():
    schedule = PeriodicRuntimeSchedule(
        trigger="component_tick",
        source="Frozen Colossus",
        interval_seconds=1.0,
        start_time_seconds=1.0,
        occurrence_count=5,
        end_time_seconds=3.0,
    )

    events = schedule_periodic_runtime_events(schedule)

    assert [event.time_seconds for event in events] == [1.0, 2.0, 3.0]


def test_periodic_schedule_must_be_bounded():
    with pytest.raises(ValueError, match="must be bounded"):
        PeriodicRuntimeSchedule(
            trigger="component_tick",
            source="Pack Leader",
            interval_seconds=2.0,
        )


def test_runtime_event_rejects_negative_or_non_finite_time():
    with pytest.raises(ValueError, match="finite non-negative"):
        RuntimeEvent(time_seconds=-0.1, trigger="tick", source="bad")

    with pytest.raises(ValueError, match="finite non-negative"):
        RuntimeEvent(time_seconds=float("inf"), trigger="tick", source="bad")
