from __future__ import annotations

from services.extreme_actual_heal_weapon_denominator_service import (
    ExtremeActualHealWeaponDenominatorService,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)
from minmax.weapon_passive_classification import VERIFIED_WEAPON_PASSIVE_RULES


class _Universe:
    def passives(self):
        return tuple(
            ExtremePlayerSkillRecord(
                skill_id=index,
                name=rule.passive,
                class_type="",
                skill_line=rule.skill_line,
                skill_type="Passive",
                is_passive=True,
                is_player=True,
                is_crafted=False,
                base_ability_id=None,
                max_rank=2,
                max_rank_ability_id=None,
                description=rule.reason,
                domain=ExtremeSkillDomain.WEAPON,
            )
            for index, rule in enumerate(VERIFIED_WEAPON_PASSIVE_RULES, start=1)
        )


class _UniverseWithUnknown(_Universe):
    def passives(self):
        return (
            *super().passives(),
            ExtremePlayerSkillRecord(
                skill_id=999,
                name="Future Weapon Passive",
                class_type="",
                skill_line="Restoration Staff",
                skill_type="Passive",
                is_passive=True,
                is_player=True,
                is_crafted=False,
                base_ability_id=None,
                max_rank=2,
                max_rank_ability_id=None,
                description="Future mechanic",
                domain=ExtremeSkillDomain.WEAPON,
            ),
        )


def test_weapon_configuration_denominator_enumerates_all_legal_bar_shapes() -> None:
    result = ExtremeActualHealWeaponDenominatorService(
        "unused.db",
        universe_service=_Universe(),
    ).build()

    assert result.legal_bar_configuration_count == 28
    assert result.legal_two_bar_configuration_count == 784
    assert result.configuration_denominator_proven is True

    by_line = {}
    for row in result.legal_bar_configurations:
        by_line[row.skill_line.value] = by_line.get(row.skill_line.value, 0) + 1

    assert by_line == {
        "bow": 1,
        "destruction_staff": 3,
        "dual_wield": 16,
        "one_hand_and_shield": 4,
        "restoration_staff": 1,
        "two_handed": 3,
    }


def test_weapon_passive_denominator_matches_reviewed_fixture() -> None:
    result = ExtremeActualHealWeaponDenominatorService(
        "unused.db",
        universe_service=_Universe(),
    ).build()

    assert result.passive_denominator_proven is True
    assert result.denominator_proven is True
    assert result.unresolved == ()
    assert len(result.canonical_weapon_passives) == len(VERIFIED_WEAPON_PASSIVE_RULES)


def test_weapon_passive_denominator_fails_closed_for_new_canonical_passive() -> None:
    result = ExtremeActualHealWeaponDenominatorService(
        "unused.db",
        universe_service=_UniverseWithUnknown(),
    ).build()

    assert result.denominator_proven is False
    assert any("Future Weapon Passive" in row for row in result.unresolved)
