from minmax.skill_component_resource_event import (
    SkillComponentResourceEventType,
    SkillComponentResourceType,
    extract_explicit_component_resource_events,
)


def test_explicit_magicka_restore_becomes_resource_event():
    events = extract_explicit_component_resource_events(
        skill_rank_id=10,
        coefficient_number=2,
        component_text="Restore $2 Magicka.",
    )

    assert len(events) == 1
    event = events[0]
    assert event.event_type is SkillComponentResourceEventType.GAINS_RESOURCE
    assert event.resource_type is SkillComponentResourceType.MAGICKA


def test_explicit_stamina_gain_is_supported():
    events = extract_explicit_component_resource_events(
        skill_rank_id=11,
        coefficient_number=1,
        component_text="Gain $1 Stamina when the effect ends.",
    )

    assert len(events) == 1
    assert events[0].resource_type is SkillComponentResourceType.STAMINA


def test_explicit_ultimate_gain_is_supported():
    events = extract_explicit_component_resource_events(
        skill_rank_id=12,
        coefficient_number=3,
        component_text="You gain $3 Ultimate.",
    )

    assert len(events) == 1
    assert events[0].resource_type is SkillComponentResourceType.ULTIMATE


def test_health_restore_is_not_a_resource_event():
    assert extract_explicit_component_resource_events(
        skill_rank_id=10,
        coefficient_number=1,
        component_text="Restore $1 Health.",
    ) == ()


def test_generic_resource_restore_without_identity_fails_closed():
    assert extract_explicit_component_resource_events(
        skill_rank_id=10,
        coefficient_number=1,
        component_text="Restore $1 resources.",
    ) == ()


def test_other_coefficient_placeholder_is_not_borrowed():
    assert extract_explicit_component_resource_events(
        skill_rank_id=10,
        coefficient_number=1,
        component_text="Deal $1 Magic Damage and restore $2 Magicka.",
    ) == ()
