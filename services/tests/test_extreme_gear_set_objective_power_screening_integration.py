from minmax.gear_sets import GearSet, GearSetBonus
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


class _Repo:
    def __init__(self, description: str):
        self.gear_set = GearSet(1, "Screened Set", "Test", 5)
        self.bonuses = (
            GearSetBonus(id=1, set_id=1, piece_count=5, description=description),
        )

    def get_set(self, name):
        return self.gear_set if name == self.gear_set.name else None

    def get_bonuses(self, set_id):
        return list(self.bonuses if int(set_id) == self.gear_set.id else ())


def _candidate(description: str):
    repository = _Repo(description)
    return ExtremeGearSetObjectiveService.candidate_for_set(
        repository,
        repository.gear_set.name,
        "weapon_damage",
    )


def test_unmapped_scaling_proc_no_longer_blocks_weapon_damage_objective() -> None:
    candidate = _candidate(
        "Deal 1000 Flame Damage. This effect scales off the higher of your Weapon or Spell Damage."
    )

    assert candidate.reviewed_delta == 0.0
    assert candidate.mechanic_complete
    assert candidate.unresolved == ()


def test_unmapped_direct_power_increase_still_fails_closed() -> None:
    candidate = _candidate(
        "When you deal damage, increase your Weapon and Spell Damage by 490 for 8 seconds."
    )

    assert not candidate.mechanic_complete
    assert any("not yet mechanic-mapped" in row for row in candidate.unresolved)
