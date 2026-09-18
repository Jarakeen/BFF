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


def test_special_h1_dispositions_split_runtime_package_and_self_irrelevant() -> None:
    resolve = ExtremeActualHealSpecialGearDenominatorService.special_h1_disposition

    assert resolve("monster", "Balorgh", "spell_damage") == "conditional"
    assert resolve("mythic", "Markyn Ring of Majesty", "weapon_damage") == "package"
    assert (
        resolve("mythic", "Oakensoul Ring", "healing_done")
        == "standing_and_package"
    )
    assert resolve("mythic", "Spaulder of Ruin", "spell_damage") == "irrelevant"
    assert (
        resolve("mythic", "Torc of the Last Ayleid King", "spell_damage")
        == "standing_and_package"
    )


def test_package_objective_counts_as_h1_relevant_without_becoming_unresolved() -> None:
    row = ExtremeActualHealSpecialGearDisposition(
        set_id=2,
        set_name="Markyn Ring of Majesty",
        family="mythic",
        relevant_objectives=(),
        conditional_objectives=(),
        package_objectives=("spell_damage", "weapon_damage"),
        unresolved=(),
    )

    assert row.h1_relevant is True
    assert row.mechanic_complete is True
