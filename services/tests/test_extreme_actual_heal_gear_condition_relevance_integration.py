from minmax.gear_sets import GearSet, GearSetBonus
from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)


class _Repo:
    def __init__(self, scoped_description: str) -> None:
        self.sets = (GearSet(1, "Scoped Power", "Test", 5),)
        self.bonuses = {
            1: (
                GearSetBonus(1, 1, 2, "Adds 129 Weapon and Spell Damage"),
                GearSetBonus(2, 1, 5, scoped_description),
            )
        }

    def list_sets(self):
        return self.sets

    def get_set(self, name):
        return self.sets[0] if name == "Scoped Power" else None

    def get_set_by_id(self, set_id):
        return self.sets[0] if int(set_id) == 1 else None

    def get_bonuses(self, set_id):
        return list(self.bonuses.get(int(set_id), ()))


def _service(description: str) -> ExtremeActualHealGearSetCandidateService:
    service = ExtremeActualHealGearSetCandidateService.__new__(
        ExtremeActualHealGearSetCandidateService
    )
    service.repository = _Repo(description)
    return service


def test_damage_type_scoped_power_does_not_disqualify_h1_set() -> None:
    service = _service("Adds 9-400 Weapon and Spell Damage to your Flame Damage abilities.")

    assert service.candidate_set_names() == ("Scoped Power",)


def test_class_scoped_power_still_disqualifies_h1_set_until_skill_scope_is_composed() -> None:
    service = _service("Adds 9-400 Weapon and Spell Damage to your Class abilities.")

    assert service.candidate_set_names() == ()
