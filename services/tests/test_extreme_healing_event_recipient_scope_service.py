from __future__ import annotations

from services.extreme_healing_event_recipient_scope_service import (
    ExtremeHealingEventRecipientScopeService,
)


def test_blood_of_the_elder_dragon_requires_recipient_selection():
    result = ExtremeHealingEventRecipientScopeService().resolve(
        ability_name="Blood of the Elder Dragon"
    )

    assert not result.single_recipient_safe
    assert result.recipient_selection_required
    assert any("distinct self and nearby-ally" in message for message in result.unresolved)


def test_legacy_coagulating_blood_name_keeps_same_boundary():
    result = ExtremeHealingEventRecipientScopeService().resolve(
        ability_name="Coagulating Blood"
    )

    assert not result.single_recipient_safe
    assert result.recipient_selection_required


def test_unmorphed_dragon_blood_is_not_blocked_by_multi_recipient_guard():
    result = ExtremeHealingEventRecipientScopeService().resolve(
        ability_name="Dragon Blood"
    )

    assert result.single_recipient_safe
    assert not result.recipient_selection_required
    assert result.unresolved == ()


def test_blood_of_the_green_dragon_is_same_recipient_even_with_hot():
    result = ExtremeHealingEventRecipientScopeService().resolve(
        ability_name="Blood of the Green Dragon"
    )

    assert result.single_recipient_safe
    assert not result.recipient_selection_required
    assert result.unresolved == ()


def test_unreviewed_ability_is_not_invented_as_multi_recipient():
    result = ExtremeHealingEventRecipientScopeService().resolve(
        ability_name="Combat Prayer"
    )

    assert result.single_recipient_safe
    assert result.unresolved == ()
