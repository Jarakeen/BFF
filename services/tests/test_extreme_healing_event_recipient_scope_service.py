from __future__ import annotations

from minmax.skill_coefficients import SkillCoefficientTrace
from services.extreme_healing_event_recipient_scope_service import (
    ExtremeHealingEventRecipientScopeService,
)


def _trace(number: int, *, a: float, b: float, c: float) -> SkillCoefficientTrace:
    max_stat = 30000.0
    power = 5000.0
    resource_term = a * max_stat
    power_term = b * power
    before_r = resource_term + power_term + c
    return SkillCoefficientTrace(
        coefficient_number=number,
        coefficient_type="8",
        max_stat=max_stat,
        power=power,
        a=a,
        b=b,
        c=c,
        r=1.0,
        resource_term=resource_term,
        power_term=power_term,
        constant_term=c,
        before_r=before_r,
        final_value=before_r,
    )


def test_blood_of_the_elder_dragon_requires_recipient_selection_without_component_proof():
    result = ExtremeHealingEventRecipientScopeService().resolve(
        ability_name="Blood of the Elder Dragon"
    )

    assert not result.single_recipient_safe
    assert result.recipient_selection_required
    assert result.selected_coefficient_numbers is None
    assert any("two-thirds" in message for message in result.unresolved)


def test_blood_of_the_elder_dragon_selects_original_scaling_as_self_heal():
    result = ExtremeHealingEventRecipientScopeService().resolve(
        ability_name="Blood of the Elder Dragon",
        heal_coefficient_numbers=(1, 2),
        coefficient_traces=(
            _trace(1, a=0.10, b=1.20, c=3.0),
            _trace(2, a=0.10 * 2.0 / 3.0, b=0.80, c=2.0),
        ),
    )

    assert result.single_recipient_safe
    assert not result.recipient_selection_required
    assert result.selected_coefficient_numbers == (1,)
    assert result.unresolved == ()


def test_dragon_blood_scaling_proof_does_not_depend_on_component_order():
    result = ExtremeHealingEventRecipientScopeService().resolve(
        ability_name="Coagulating Blood",
        heal_coefficient_numbers=(9, 4),
        coefficient_traces=(
            _trace(4, a=0.12, b=1.50, c=-3.0),
            _trace(9, a=0.08, b=1.00, c=-2.0),
        ),
    )

    assert result.single_recipient_safe
    assert result.selected_coefficient_numbers == (4,)


def test_dragon_blood_keeps_ambiguous_coefficients_unresolved():
    result = ExtremeHealingEventRecipientScopeService().resolve(
        ability_name="Blood of the Elder Dragon",
        heal_coefficient_numbers=(1, 2),
        coefficient_traces=(
            _trace(1, a=0.10, b=1.20, c=3.0),
            _trace(2, a=0.07, b=0.80, c=2.0),
        ),
    )

    assert not result.single_recipient_safe
    assert result.recipient_selection_required
    assert result.selected_coefficient_numbers is None


def test_dragon_blood_requires_exactly_two_heal_components_for_scaling_proof():
    result = ExtremeHealingEventRecipientScopeService().resolve(
        ability_name="Blood of the Elder Dragon",
        heal_coefficient_numbers=(1, 2, 3),
        coefficient_traces=(
            _trace(1, a=0.10, b=1.20, c=3.0),
            _trace(2, a=0.10 * 2.0 / 3.0, b=0.80, c=2.0),
            _trace(3, a=0.01, b=0.02, c=0.0),
        ),
    )

    assert not result.single_recipient_safe
    assert result.selected_coefficient_numbers is None


def test_unmorphed_dragon_blood_is_not_blocked_by_multi_recipient_guard():
    result = ExtremeHealingEventRecipientScopeService().resolve(
        ability_name="Dragon Blood"
    )

    assert result.single_recipient_safe
    assert not result.recipient_selection_required
    assert result.selected_coefficient_numbers is None
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
