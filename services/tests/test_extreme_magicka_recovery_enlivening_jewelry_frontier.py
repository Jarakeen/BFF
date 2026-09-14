from minmax.base_character_state import BASE_MAX_MAGICKA
from minmax.conditional_recovery import enlivening_overflow_recovery_bonus
from tools.audit_extreme_magicka_recovery_enlivening_jewelry_frontier import (
    arcane_variant_upper_bound,
    conservative_three_infused_total,
    enlivening_cap_requirement,
)


def test_enlivening_cap_requires_30000_max_magicka():
    assert enlivening_cap_requirement() == 30000.0


def test_base_max_magicka_already_supplies_sixty_enlivening_recovery():
    assert BASE_MAX_MAGICKA == 12000.0
    assert enlivening_overflow_recovery_bonus(int(BASE_MAX_MAGICKA)) == 60


def test_one_arcane_slot_cannot_overcome_lost_infused_recovery_even_with_full_cap():
    three_infused_total = conservative_three_infused_total(
        three_infused_recovery=811.2,
    )
    result = arcane_variant_upper_bound(
        arcane_slots=1,
        base_glyph_recovery=169.0,
        infused_glyph_recovery=270.4,
        three_infused_conservative_total=three_infused_total,
    )

    assert three_infused_total == 871.2
    assert result.direct_recovery == 709.8
    assert result.total_recovery_upper_bound == 859.8
    assert result.dominated_by_three_infused is True


def test_two_and_three_arcane_slots_are_also_globally_dominated():
    three_infused_total = conservative_three_infused_total(
        three_infused_recovery=811.2,
    )

    two_arcane = arcane_variant_upper_bound(
        arcane_slots=2,
        base_glyph_recovery=169.0,
        infused_glyph_recovery=270.4,
        three_infused_conservative_total=three_infused_total,
    )
    three_arcane = arcane_variant_upper_bound(
        arcane_slots=3,
        base_glyph_recovery=169.0,
        infused_glyph_recovery=270.4,
        three_infused_conservative_total=three_infused_total,
    )

    assert two_arcane.total_recovery_upper_bound == 758.4
    assert two_arcane.dominated_by_three_infused is True
    assert three_arcane.total_recovery_upper_bound == 657.0
    assert three_arcane.dominated_by_three_infused is True
