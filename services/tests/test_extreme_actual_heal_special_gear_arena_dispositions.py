from __future__ import annotations

from services.extreme_actual_heal_special_gear_denominator_service import (
    ExtremeActualHealSpecialGearDenominatorService,
    ExtremeActualHealSpecialGearDisposition,
)


def test_arena_h1_dispositions_cover_standing_conditional_and_irrelevant_cases() -> None:
    resolve = ExtremeActualHealSpecialGearDenominatorService.arena_h1_disposition

    assert resolve("Perfected Grand Rejuvenation", "max_magicka") == "standing"
    assert resolve("Chaotic Whirlwind", "spell_damage") == "conditional"
    assert (
        resolve("Perfected Destructive Impact", "weapon_damage")
        == "standing_and_conditional"
    )
    assert resolve("Puncturing Remedy", "healing_done") == "irrelevant"
    assert resolve("Grand Rejuvenation", "spell_damage") is None


def test_conditional_objective_counts_as_h1_relevant_without_becoming_unresolved() -> None:
    row = ExtremeActualHealSpecialGearDisposition(
        set_id=1,
        set_name="Chaotic Whirlwind",
        family="arena_weapon",
        relevant_objectives=(),
        conditional_objectives=("spell_damage", "weapon_damage"),
        unresolved=(),
    )

    assert row.h1_relevant is True
    assert row.mechanic_complete is True
