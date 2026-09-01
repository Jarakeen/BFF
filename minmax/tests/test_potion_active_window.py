from __future__ import annotations

from minmax.combat_state import CombatState
from minmax.potion_active_window import PotionActiveWindow
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


def test_active_window_exposes_named_buffs_before_expiry() -> None:
    window = PotionActiveWindow(_event(), elapsed_seconds=36.5)

    assert window.active_buff_names == (
        "Major Intellect",
        "Major Sorcery",
        "Major Prophecy",
    )


def test_active_window_expires_grants_at_sourced_duration_boundary() -> None:
    window = PotionActiveWindow(_event(), elapsed_seconds=36.6)

    assert window.active_buff_grants == ()
    assert window.active_buff_names == ()


def test_active_window_merges_into_explicit_combat_state_without_overwriting_existing_buffs() -> None:
    base = CombatState(in_combat=True, active_buffs=("Major Resolve",))

    state = PotionActiveWindow(_event(), elapsed_seconds=12.0).to_combat_state(base)

    assert state.in_combat is True
    assert state.active_buffs == (
        "Major Resolve",
        "Major Intellect",
        "Major Sorcery",
        "Major Prophecy",
    )


def test_negative_elapsed_time_fails_closed() -> None:
    try:
        PotionActiveWindow(_event(), elapsed_seconds=-0.1)
    except ValueError as exc:
        assert "cannot be negative" in str(exc)
    else:
        raise AssertionError("negative elapsed time should fail")
