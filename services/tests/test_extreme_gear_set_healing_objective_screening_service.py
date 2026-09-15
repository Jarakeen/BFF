from __future__ import annotations

import pytest

from services.extreme_gear_set_healing_objective_screening_service import (
    ExtremeGearSetHealingObjectiveScreeningService,
)


def test_damage_proc_is_irrelevant_to_healing_done_sheet_stat() -> None:
    result = ExtremeGearSetHealingObjectiveScreeningService.review(
        "When you deal damage, summon a creature that deals 5000 Shock Damage.",
        "healing_done",
    )

    assert result.proven_irrelevant is True
    assert result.blockers == ()


def test_heal_proc_is_irrelevant_to_healing_done_sheet_stat() -> None:
    result = ExtremeGearSetHealingObjectiveScreeningService.review(
        "When you take damage, heal yourself for an unknown amount.",
        "healing_done",
    )

    assert result.proven_irrelevant is True
    assert result.blockers == ()


def test_direct_healing_done_reference_stays_blocking() -> None:
    result = ExtremeGearSetHealingObjectiveScreeningService.review(
        "While on your back bar, increase your Healing Done by 14%.",
        "healing_done",
    )

    assert result.proven_irrelevant is False
    assert any("Healing Done" in item for item in result.healing_hazards)


def test_mending_reference_stays_blocking_for_healing_done() -> None:
    result = ExtremeGearSetHealingObjectiveScreeningService.review(
        "Gain Major Mending while standing in the area.",
        "healing_done",
    )

    assert result.proven_irrelevant is False
    assert any("Mending" in item for item in result.healing_hazards)


def test_plain_damage_critical_language_is_irrelevant_to_critical_healing() -> None:
    result = ExtremeGearSetHealingObjectiveScreeningService.review(
        "Critical damage causes an explosion that deals Flame Damage.",
        "critical_healing",
    )

    assert result.proven_irrelevant is True


def test_critical_heal_trigger_is_not_a_critical_healing_stat_modifier() -> None:
    result = ExtremeGearSetHealingObjectiveScreeningService.review(
        "When your healing critically strikes, grant the target a damage shield.",
        "critical_healing",
    )

    assert result.proven_irrelevant is True
    assert result.blockers == ()


def test_critical_healing_language_stays_blocking() -> None:
    result = ExtremeGearSetHealingObjectiveScreeningService.review(
        "Your Critical Healing is increased by an unknown amount.",
        "critical_healing",
    )

    assert result.proven_irrelevant is False
    assert result.healing_hazards


def test_group_member_bonus_that_excludes_wearer_is_irrelevant_to_self_h1() -> None:
    result = ExtremeGearSetHealingObjectiveScreeningService.review(
        "While you have more than 50% Health, the Critical Damage and Critical Healing of "
        "any group members not wearing Lucent Echoes within 28 meters of you increases by 11%.",
        "critical_healing",
    )

    assert result.proven_irrelevant is True
    assert result.wearer_excluded is True
    assert result.healing_hazards == ()


def test_group_member_exclusion_does_not_override_global_equipment_hazard() -> None:
    result = ExtremeGearSetHealingObjectiveScreeningService.review(
        "The Critical Healing of group members not wearing this set increases by 10%, "
        "and you can have two Mundus Stone boons at the same time.",
        "critical_healing",
    )

    assert result.wearer_excluded is True
    assert result.proven_irrelevant is False
    assert result.global_equipment_hazards


def test_opaque_text_stays_unresolved_without_positive_mechanic_evidence() -> None:
    result = ExtremeGearSetHealingObjectiveScreeningService.review(
        "An unresolved bonus worth an unknown amount.",
        "healing_done",
    )

    assert result.proven_irrelevant is False
    assert result.unrelated_mechanic_evidence == ()


def test_global_equipment_mutation_stays_blocking() -> None:
    result = ExtremeGearSetHealingObjectiveScreeningService.review(
        "Disable all other item set bonuses while this effect is active.",
        "critical_healing",
    )

    assert result.proven_irrelevant is False
    assert result.global_equipment_hazards


def test_unknown_objective_is_rejected() -> None:
    with pytest.raises(KeyError, match="unreviewed Extreme healing screening objective"):
        ExtremeGearSetHealingObjectiveScreeningService.review(
            "Deals Flame Damage.",
            "healing_received",
        )
