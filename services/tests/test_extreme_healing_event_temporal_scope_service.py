from services.extreme_healing_event_temporal_scope_service import (
    ExtremeHealingEventTemporalScopeService,
)


def test_green_dragon_blood_requires_component_time_selection():
    result = ExtremeHealingEventTemporalScopeService().resolve(
        ability_name="Blood of the Green Dragon"
    )

    assert not result.single_instant_safe
    assert result.component_time_selection_required
    assert any("immediate heal plus later healing over time" in message for message in result.unresolved)


def test_legacy_green_dragon_blood_name_has_same_boundary():
    result = ExtremeHealingEventTemporalScopeService().resolve(
        ability_name="Green Dragon Blood"
    )

    assert not result.single_instant_safe
    assert result.component_time_selection_required


def test_unmorphed_dragon_blood_is_single_instant_safe():
    result = ExtremeHealingEventTemporalScopeService().resolve(
        ability_name="Dragon Blood"
    )

    assert result.single_instant_safe
    assert not result.component_time_selection_required
    assert result.unresolved == ()


def test_elder_dragon_temporal_guard_does_not_duplicate_recipient_scope_boundary():
    result = ExtremeHealingEventTemporalScopeService().resolve(
        ability_name="Blood of the Elder Dragon"
    )

    assert result.single_instant_safe
    assert result.unresolved == ()


def test_unrelated_heal_is_unchanged():
    result = ExtremeHealingEventTemporalScopeService().resolve(
        ability_name="Combat Prayer"
    )

    assert result.single_instant_safe
    assert result.unresolved == ()
