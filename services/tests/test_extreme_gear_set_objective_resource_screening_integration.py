from minmax.gear_sets import GearSet, GearSetBonus
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


class _Repo:
    def __init__(self, gear_set, bonuses):
        self.gear_set = gear_set
        self.bonuses = tuple(bonuses)

    def list_sets(self):
        return (self.gear_set,)

    def get_set(self, name):
        return self.gear_set if name == self.gear_set.name else None

    def get_bonuses(self, set_id):
        return list(self.bonuses if int(set_id) == int(self.gear_set.id) else ())


def _candidate(description: str, objective: str):
    gear_set = GearSet(1, "Screened Set", "Test", 5)
    repo = _Repo(
        gear_set,
        (
            GearSetBonus(
                id=1,
                set_id=1,
                piece_count=5,
                description=description,
            ),
        ),
    )
    return ExtremeGearSetObjectiveService.candidate_for_set(
        repo,
        gear_set.name,
        objective,
    )


def test_unmapped_unrelated_proc_no_longer_blocks_max_resource_objective():
    row = _candidate(
        "(5 items) When you deal damage, summon a creature that deals Shock Damage every 2 seconds.",
        "max_magicka",
    )

    assert row.reviewed_delta == 0.0
    assert row.mechanic_complete is True
    assert row.unresolved == ()


def test_same_unmapped_proc_still_blocks_non_resource_objective():
    row = _candidate(
        "(5 items) When you deal damage, summon a creature that deals Shock Damage every 2 seconds.",
        "spell_damage",
    )

    assert row.mechanic_complete is False
    assert any("not yet mechanic-mapped" in item for item in row.unresolved)


def test_unmapped_target_resource_reference_remains_blocker():
    row = _candidate(
        "(5 items) While you have a pet active, your Max Magicka is increased by 3132.",
        "max_magicka",
    )

    assert row.mechanic_complete is False
    assert any("Max Magicka" in item for item in row.unresolved)


def test_unmapped_resource_scaling_reference_is_proven_irrelevant_to_resource_maximum():
    row = _candidate(
        "(5 items) The heal scales off the higher of your Max Magicka or Stamina.",
        "max_magicka",
    )

    assert row.reviewed_delta == 0.0
    assert row.mechanic_complete is True
    assert row.unresolved == ()


def test_global_equipment_rule_remains_blocker_without_target_resource_text():
    row = _candidate(
        "(1 item) Adds 1337 Weapon and Spell Damage. Disable all other item set bonuses.",
        "max_health",
    )

    assert row.mechanic_complete is False
    assert row.unresolved
