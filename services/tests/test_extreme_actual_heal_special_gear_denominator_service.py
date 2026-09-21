from __future__ import annotations

from dataclasses import dataclass

from services.extreme_actual_heal_special_gear_denominator_service import (
    H1_GEAR_OBJECTIVES,
    ExtremeActualHealSpecialGearDenominator,
    ExtremeActualHealSpecialGearDisposition,
)


def test_special_gear_denominator_summary_counts_families_and_fail_closed_rows() -> None:
    report = ExtremeActualHealSpecialGearDenominator(
        rows=(
            ExtremeActualHealSpecialGearDisposition(
                1, "Monster A", "monster", ("healing_done",), ()
            ),
            ExtremeActualHealSpecialGearDisposition(
                2, "Mythic A", "mythic", (), ()
            ),
            ExtremeActualHealSpecialGearDisposition(
                3,
                "Arena A",
                "arena_weapon",
                (),
                unresolved=("spell_damage: unresolved",),
            ),
        )
    )

    assert report.monster_count == 1
    assert report.mythic_count == 1
    assert report.arena_weapon_count == 1
    assert len(report.relevant_rows) == 1
    assert len(report.unresolved_rows) == 1
    assert report.denominator_proven is False


def test_h1_special_gear_objective_denominator_is_explicit() -> None:
    assert H1_GEAR_OBJECTIVES == (
        "healing_done",
        "critical_healing",
        "spell_damage",
        "weapon_damage",
        "max_health",
        "max_magicka",
        "max_stamina",
    )
