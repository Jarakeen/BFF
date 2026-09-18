from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.derived_stats import DerivedStatCalculator, DerivedStatInputs, StatContribution
from minmax.stat_ids import StatId
from models.build_model import GearSlot, PlayerBuild
from services.extreme_actual_heal_weapon_passive_power_service import (
    ExtremeActualHealWeaponPassivePowerService,
)


class _Progression:
    def __init__(self, ranks):
        self.ranks = dict(ranks)

    def passive_rank(self, name):
        return self.ranks.get(name)


class _SkillLines:
    @staticmethod
    def passive_max_rank(_name):
        return 2


def _context(*, ranks, flat=3000.0, percent=0.20):
    inputs = DerivedStatInputs(
        flat=(StatContribution("existing flat", flat),),
        percent=(StatContribution("existing percent", percent),),
    )
    calculator = DerivedStatCalculator()
    return SimpleNamespace(
        progression=_Progression(ranks),
        core_state=SimpleNamespace(
            derived={
                StatId.WEAPON_DAMAGE: calculator.weapon_damage(inputs),
                StatId.SPELL_DAMAGE: calculator.spell_damage(inputs),
            }
        ),
    )


def _service():
    return ExtremeActualHealWeaponPassivePowerService(
        "unused.db",
        skill_line_repository=_SkillLines(),
    )


def test_dual_swords_project_twin_blade_and_ambidextrous_through_sheet_percent() -> None:
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(
            WeaponType="Sword", Quality="Gold", Level="CP160"
        ),
        FrontBarOffHand=GearSlot(
            WeaponType="Sword", Quality="Gold", Level="CP160"
        ),
    )
    result = _service().resolve(
        build=build,
        context=_context(
            ranks={"Twin Blade and Blunt": 2, "Ambidextrous": 2}
        ),
    )

    expected_pre_percent_flat = 128.0 + 1335.0 * 0.03
    assert result.power_bonus == pytest.approx(
        round(expected_pre_percent_flat * 1.20),
        abs=1.0,
    )
    assert set(result.sources) == {
        "Twin Blade and Blunt: 2 sword(s)",
        "Ambidextrous",
    }
    assert result.unresolved == ()


def test_sword_and_board_adds_to_existing_percent_bucket_not_after_it() -> None:
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(WeaponType="Sword"),
        FrontBarOffHand=GearSlot(WeaponType="Shield"),
    )
    result = _service().resolve(
        build=build,
        context=_context(ranks={"Sword and Board": 2}),
    )

    # Base + existing flat = 4000 before the 20% bucket, so another additive 3%
    # contributes 120 sheet power, not 3% of the already-multiplied 4800.
    assert result.power_bonus == pytest.approx(120.0)
    assert result.sources == ("Sword and Board",)
    assert result.unresolved == ()


def test_greatsword_gets_heavy_weapons_but_battleaxe_does_not() -> None:
    context = _context(ranks={"Heavy Weapons": 2})
    greatsword = PlayerBuild(FrontBarWeapon=GearSlot(WeaponType="Greatsword"))
    battleaxe = PlayerBuild(FrontBarWeapon=GearSlot(WeaponType="Battleaxe"))

    great = _service().resolve(build=greatsword, context=context)
    axe = _service().resolve(build=battleaxe, context=context)

    assert great.power_bonus == pytest.approx(155.0, abs=1.0)
    assert great.sources == ("Heavy Weapons: Greatsword",)
    assert axe.power_bonus == 0.0
    assert axe.sources == ()


def test_missing_rank_fails_closed_when_configuration_has_relevant_passive() -> None:
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(WeaponType="Sword"),
        FrontBarOffHand=GearSlot(WeaponType="Shield"),
    )
    result = _service().resolve(
        build=build,
        context=_context(ranks={}),
    )

    assert result.power_bonus == 0.0
    assert any("Sword and Board" in row for row in result.unresolved)
