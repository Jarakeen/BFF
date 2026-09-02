from minmax.skill_component_current_bonus import (
    SkillComponentCurrentBonusDriver,
    SkillComponentCurrentBonusMode,
    extract_explicit_component_current_bonus,
)
from minmax.stat_ids import StatId


def test_light_armor_penetration_current_bonus_is_explicit_aggregate():
    rows = extract_explicit_component_current_bonus(
        skill_rank_id=1,
        coefficient_number=1,
        component_text=(
            "Increases your Physical and Spell Penetration by 939 for each piece of Light Armor worn. "
            "Current bonus: $1"
        ),
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.stats == (StatId.PHYSICAL_PENETRATION, StatId.SPELL_PENETRATION)
    assert row.driver == SkillComponentCurrentBonusDriver.LIGHT_ARMOR_PIECES_EQUIPPED
    assert row.mode == SkillComponentCurrentBonusMode.FLAT_PER_UNIT
    assert row.amount_per_unit == 939.0


def test_wellspring_current_bonus_routes_to_all_three_recoveries():
    rows = extract_explicit_component_current_bonus(
        skill_rank_id=2,
        coefficient_number=1,
        component_text=(
            "Increasing your Health, Magicka, and Stamina Recovery by 81 for each Soldier of Apocrypha ability slotted. "
            "Current bonus: $1."
        ),
    )
    assert len(rows) == 1
    assert rows[0].stats == (StatId.HEALTH_RECOVERY, StatId.MAGICKA_RECOVERY, StatId.STAMINA_RECOVERY)
    assert rows[0].driver == SkillComponentCurrentBonusDriver.SOLDIER_OF_APOCRYPHA_ABILITIES_SLOTTED


def test_bare_current_bonus_does_not_promote():
    assert extract_explicit_component_current_bonus(
        skill_rank_id=3,
        coefficient_number=1,
        component_text="Current bonus: $1.",
    ) == ()


def test_wrong_placeholder_does_not_promote():
    assert extract_explicit_component_current_bonus(
        skill_rank_id=4,
        coefficient_number=2,
        component_text=(
            "Increases your Spell Resistance by 726 for each piece of Light Armor equipped. Current bonus: $1."
        ),
    ) == ()
