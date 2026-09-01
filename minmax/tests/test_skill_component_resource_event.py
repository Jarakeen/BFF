from minmax.skill_component_resource_event import (
    SkillComponentResourceAmountBasis,
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
    assert event.amount_basis is SkillComponentResourceAmountBasis.COEFFICIENT
    assert event.amount_fraction is None


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


def test_percent_of_missing_resource_is_supported():
    events = extract_explicit_component_resource_events(
        skill_rank_id=13,
        coefficient_number=1,
        component_text="Deal $1 Magic Damage and restore 7% of your missing Stamina.",
    )

    assert len(events) == 1
    event = events[0]
    assert event.resource_type is SkillComponentResourceType.STAMINA
    assert event.amount_basis is SkillComponentResourceAmountBasis.PERCENT_MISSING
    assert event.amount_fraction == 0.07


def test_percent_of_missing_two_named_resources_emits_two_events():
    events = extract_explicit_component_resource_events(
        skill_rank_id=14,
        coefficient_number=1,
        component_text=(
            "Restore 15% of your missing Magicka and Stamina and heal $1 Health."
        ),
    )

    assert [(event.resource_type, event.amount_fraction) for event in events] == [
        (SkillComponentResourceType.MAGICKA, 0.15),
        (SkillComponentResourceType.STAMINA, 0.15),
    ]


def test_percent_resource_event_requires_current_component_placeholder():
    assert extract_explicit_component_resource_events(
        skill_rank_id=14,
        coefficient_number=2,
        component_text="Restore 15% of your missing Magicka and heal $1 Health.",
    ) == ()


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
