from minmax.skill_component_source_stat_rule import (
    SkillComponentSourceStatRuleBasis,
    SkillComponentSourceStatRuleDriver,
    extract_source_mapped_stat_rule,
)
from minmax.stat_ids import StatId


def test_twin_blade_mace_penetration_uses_raw_slot_alignment():
    rows = extract_source_mapped_stat_rule(
        skill_rank_id=5653,
        coefficient_number=2,
        raw_description=(
            "Each axe increases your Critical Damage done by <<1>>. "
            "Each mace increases your Offensive Penetration by <<2>>. "
            "Each sword increases your Weapon and Spell Damage by <<3>>."
        ),
        coef_description=(
            "Each axe increases your Critical Damage done by 3%. "
            "Each mace increases your Offensive Penetration by 743. "
            "Each sword increases your Weapon and Spell Damage by 64."
        ),
    )
    assert len(rows) == 1
    assert rows[0].driver is SkillComponentSourceStatRuleDriver.DUAL_WIELD_MACES_EQUIPPED
    assert rows[0].amount_basis is SkillComponentSourceStatRuleBasis.FLAT_PER_UNIT
    assert rows[0].amount == 743
    assert rows[0].stats == (StatId.PHYSICAL_PENETRATION, StatId.SPELL_PENETRATION)


def test_twin_blade_accepts_color_tagged_literal_source():
    rows = extract_source_mapped_stat_rule(
        skill_rank_id=5654,
        coefficient_number=2,
        raw_description="Each mace increases your Offensive Penetration by <<2>>.",
        coef_description="Each mace increases your Offensive Penetration by |cffffff1487|r.",
    )
    assert len(rows) == 1
    assert rows[0].amount == 1487


def test_twin_blade_survives_raw_display_sentence_drift():
    rows = extract_source_mapped_stat_rule(
        skill_rank_id=5654,
        coefficient_number=2,
        raw_description=(
            "With one of each weapon type equipped, gain an extra benefit. "
            "Each mace increases your Offensive Penetration by <<2>>."
        ),
        coef_description=(
            "Gain bonuses based on each weapon equipped: each axe increases Critical Damage. "
            "Weapon bonuses are calculated independently. "
            "Each mace increases your Offensive Penetration by |cffffff1487|r."
        ),
    )
    assert len(rows) == 1
    assert rows[0].amount == 1487


def test_death_knell_preserves_threshold_amount_and_canonical_slot_requirement():
    rows = extract_source_mapped_stat_rule(
        skill_rank_id=7390,
        coefficient_number=1,
        raw_description="Increases your Critical Strike Chance against enemies under 33% Health by <<1>>.",
        coef_description="Increases your Critical Strike Chance against enemies under 33% Health by 10%.",
        desc_header="WITH A GRAVE LORD ABILITY SLOTTED",
    )
    assert len(rows) == 1
    assert rows[0].driver is SkillComponentSourceStatRuleDriver.GRAVELORD_ABILITY_SLOTTED
    assert rows[0].amount_basis is SkillComponentSourceStatRuleBasis.CONDITIONAL_FRACTION
    assert rows[0].amount == 0.10
    assert rows[0].target_health_below_fraction == 0.33
    assert rows[0].stats == (StatId.CRITICAL_CHANCE,)


def test_death_knell_accepts_color_tagged_literal_source():
    rows = extract_source_mapped_stat_rule(
        skill_rank_id=7391,
        coefficient_number=1,
        raw_description="Increases your Critical Strike Chance against enemies under 33% Health by <<1>>.",
        coef_description=(
            "Increases your Critical Strike Chance against enemies under |cffffff33|r% Health "
            "by |cffffff20|r%."
        ),
        desc_header="WITH A GRAVE LORD ABILITY SLOTTED",
    )
    assert len(rows) == 1
    assert rows[0].amount == 0.20
    assert rows[0].target_health_below_fraction == 0.33


def test_death_knell_still_accepts_compact_gravelord_header():
    rows = extract_source_mapped_stat_rule(
        skill_rank_id=7390,
        coefficient_number=1,
        raw_description="Increases your Critical Strike Chance against enemies under 33% Health by <<1>>.",
        coef_description="Increases your Critical Strike Chance against enemies under 33% Health by 10%.",
        desc_header="WITH A GRAVELORD ABILITY SLOTTED",
    )
    assert len(rows) == 1


def test_death_knell_rejects_unrelated_slot_header():
    rows = extract_source_mapped_stat_rule(
        skill_rank_id=7390,
        coefficient_number=1,
        raw_description="Increases your Critical Strike Chance against enemies under 33% Health by <<1>>.",
        coef_description="Increases your Critical Strike Chance against enemies under 33% Health by 10%.",
        desc_header="WITH A BONE TYRANT ABILITY SLOTTED",
    )
    assert rows == ()


def test_raw_slot_alignment_does_not_invent_unrelated_semantics():
    rows = extract_source_mapped_stat_rule(
        skill_rank_id=4500,
        coefficient_number=3,
        raw_description="Deal <<1>> every <<2>> in a channeled attack over <<3>>.",
        coef_description="Deal $1 Flame Damage every 0.5 seconds in a channeled attack over 4.8 seconds.",
    )
    assert rows == ()
