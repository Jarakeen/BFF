from __future__ import annotations

from minmax.potion_cadence import PotionCadence, medicinal_use_duration_multiplier
from minmax.potion_use_event import PotionBuffGrant, PotionUseEvent


def _event() -> PotionUseEvent:
    return PotionUseEvent(
        selected_label="spell power",
        buff_grants=(
            PotionBuffGrant("Restore Magicka", "Major Intellect", 36.6, 40.6, "Essence of Magicka"),
            PotionBuffGrant("Increase Spell Power", "Major Sorcery", 36.6, 40.6, "Essence of Spell Power"),
            PotionBuffGrant("Spell Critical", "Major Prophecy", 36.6, 40.6, "Essence of Spell Critical"),
        ),
    )


def test_medicinal_use_rank_multipliers_are_explicit() -> None:
    assert medicinal_use_duration_multiplier(0) == 1.0
    assert medicinal_use_duration_multiplier(1) == 1.1
    assert medicinal_use_duration_multiplier(2) == 1.2
    assert medicinal_use_duration_multiplier(3) == 1.3


def test_rank_zero_has_gap_before_default_potion_cooldown() -> None:
    cadence = PotionCadence(_event(), medicinal_use_rank=0)

    assert cadence.minimum_buff_duration == 36.6
    assert cadence.cooldown_seconds == 45.0
    assert cadence.guaranteed_gap_seconds == 8.4
    assert cadence.guaranteed_overlap_seconds == 0.0
    assert not cadence.can_refresh_before_all_buffs_expire()


def test_rank_three_extends_36_6_second_buffs_to_47_58_seconds() -> None:
    cadence = PotionCadence(_event(), medicinal_use_rank=3)

    assert abs(cadence.minimum_buff_duration - 47.58) < 1e-9
    assert abs(cadence.guaranteed_overlap_seconds - 2.58) < 1e-9
    assert cadence.guaranteed_gap_seconds == 0.0
    assert cadence.can_refresh_before_all_buffs_expire()


def test_rank_three_active_window_uses_adjusted_duration() -> None:
    cadence = PotionCadence(_event(), medicinal_use_rank=3)

    assert cadence.window(45.0).active_buff_names == (
        "Major Intellect",
        "Major Sorcery",
        "Major Prophecy",
    )
    assert cadence.window(47.58).active_buff_names == ()


def test_invalid_medicinal_use_rank_fails_closed() -> None:
    try:
        PotionCadence(_event(), medicinal_use_rank=4)
    except ValueError as exc:
        assert "between 0 and 3" in str(exc)
    else:
        raise AssertionError("invalid Medicinal Use rank should fail")
