from services.rotation_lokkestiiz_healer_scenario import (
    build_magrat_df_healer_lokkestiiz_scenario,
)
from tools.audit_phase13_lokkestiiz_healer_profile import _apply_boss_replacements


def test_audit_applies_winters_revenge_to_elemental_blockade_swap() -> None:
    scenario = build_magrat_df_healer_lokkestiiz_scenario()
    base = {
        "elemental_susceptibility": ("back", 1, "Elemental Susceptibility"),
        "winters_revenge": ("back", 3, "Winter's Revenge"),
    }

    effective, notes = _apply_boss_replacements(base, scenario.skill_replacements)

    assert "winters_revenge" not in effective
    assert effective["elemental_blockade"] == ("back", 3, "Elemental Blockade")
    assert notes == (
        "back slot 3: winters_revenge -> elemental_blockade",
    )


def test_audit_rejects_stale_boss_loadout_source_slot() -> None:
    scenario = build_magrat_df_healer_lokkestiiz_scenario()
    base = {
        "winters_revenge": ("front", 3, "Winter's Revenge"),
    }

    try:
        _apply_boss_replacements(base, scenario.skill_replacements)
    except ValueError as exc:
        assert "expected back, got front" in str(exc)
    else:
        raise AssertionError("stale boss loadout source bar should be rejected")
