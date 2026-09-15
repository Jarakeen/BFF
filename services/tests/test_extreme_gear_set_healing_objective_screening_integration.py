from __future__ import annotations

from minmax.gear_sets import GearSet, GearSetBonus
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


class _Repo:
    def __init__(self, description: str) -> None:
        self.gear_set = GearSet(1, "Screened Set", "Test", 5)
        self.bonus = GearSetBonus(1, 1, 5, description)

    def list_sets(self):
        return (self.gear_set,)

    def get_set(self, name):
        return self.gear_set if name == self.gear_set.name else None

    def get_bonuses(self, set_id):
        return [self.bonus] if int(set_id) == 1 else []


def test_unmapped_damage_proc_does_not_block_healing_done_objective() -> None:
    row = ExtremeGearSetObjectiveService.candidate_for_set(
        _Repo("When you deal damage, deal 5000 Flame Damage to the enemy."),
        "Screened Set",
        "healing_done",
    )

    assert row.reviewed_delta == 0.0
    assert row.mechanic_complete is True
    assert row.unresolved == ()


def test_unmapped_heal_proc_does_not_block_healing_done_sheet_objective() -> None:
    row = ExtremeGearSetObjectiveService.candidate_for_set(
        _Repo("When you take damage, heal yourself for an unknown amount."),
        "Screened Set",
        "healing_done",
    )

    assert row.reviewed_delta == 0.0
    assert row.mechanic_complete is True
    assert row.unresolved == ()


def test_unmapped_damage_critical_text_does_not_block_critical_healing() -> None:
    row = ExtremeGearSetObjectiveService.candidate_for_set(
        _Repo("Critical damage causes an explosion that deals Flame Damage."),
        "Screened Set",
        "critical_healing",
    )

    assert row.mechanic_complete is True
    assert row.unresolved == ()


def test_unmapped_crit_heal_trigger_does_not_block_critical_healing_sheet_objective() -> None:
    row = ExtremeGearSetObjectiveService.candidate_for_set(
        _Repo("When your healing critically strikes, grant the target a damage shield."),
        "Screened Set",
        "critical_healing",
    )

    assert row.reviewed_delta == 0.0
    assert row.mechanic_complete is True
    assert row.unresolved == ()


def test_group_member_modifier_that_excludes_wearer_does_not_block_self_h1() -> None:
    row = ExtremeGearSetObjectiveService.candidate_for_set(
        _Repo(
            "While you have more than 50% Health, the Critical Damage and Critical Healing of "
            "any group members not wearing Lucent Echoes within 28 meters of you increases by 11%."
        ),
        "Screened Set",
        "critical_healing",
    )

    assert row.reviewed_delta == 0.0
    assert row.mechanic_complete is True
    assert row.unresolved == ()


def test_unmapped_critical_healing_modifier_still_blocks_critical_healing() -> None:
    row = ExtremeGearSetObjectiveService.candidate_for_set(
        _Repo("Your Critical Healing is increased by an unknown amount."),
        "Screened Set",
        "critical_healing",
    )

    assert row.mechanic_complete is False
    assert row.unresolved
