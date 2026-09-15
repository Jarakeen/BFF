from minmax.gear_sets import GearSet, GearSetBonus
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


class _Repo:
    def __init__(self, name: str, description: str) -> None:
        self.gear_set = GearSet(1, name, "Test", 5)
        self.bonus = GearSetBonus(1, 1, 5, description)

    def list_sets(self):
        return (self.gear_set,)

    def get_set(self, name):
        return self.gear_set if name == self.gear_set.name else None

    def get_bonuses(self, set_id):
        return [self.bonus] if int(set_id) == 1 else []


def _row(name: str, description: str, objective: str):
    return ExtremeGearSetObjectiveService.candidate_for_set(
        _Repo(name, description),
        name,
        objective,
    )


def test_food_condition_can_prove_green_pact_max_health_delta() -> None:
    row = _row(
        "Green Pact",
        "(5 items) While you have a food buff active, your Max Health is increased by "
        "58-2500 and Health Recovery by 8-356.",
        "max_health",
    )

    assert row.reviewed_delta == 2500.0
    assert row.mechanic_complete is True
    assert row.unresolved == ()


def test_drink_condition_can_prove_bright_throat_max_magicka_delta() -> None:
    row = _row(
        "Bright-Throat's Boast",
        "(5 items) While you have a drink buff active, your Max Magicka is increased by "
        "46-2000 and Magicka Recovery by 3-133.",
        "max_magicka",
    )

    assert row.reviewed_delta == 2000.0
    assert row.mechanic_complete is True


def test_pet_condition_can_prove_necropotence_max_magicka_delta() -> None:
    row = _row(
        "Necropotence",
        "(5 items) While you have a pet active, your Max Magicka is increased by 72-3132.",
        "max_magicka",
    )

    assert row.reviewed_delta == 3132.0
    assert row.mechanic_complete is True


def test_self_group_aura_can_prove_ebon_wearer_max_health_delta() -> None:
    row = _row(
        "Ebon Armory",
        "(5 items) Increases Max Health by 23-1000 for you and up to 11 other group members "
        "within 28 meters of you. This bonus persists through death.",
        "max_health",
    )

    assert row.reviewed_delta == 1000.0
    assert row.mechanic_complete is True


def test_self_group_aura_can_prove_xoryn_both_resource_objectives() -> None:
    description = (
        "(5 items) Increases Max Magicka and Max Stamina by 1667 for you and up to 11 other "
        "group members within 28 meters of you. This bonus persists through death."
    )
    magicka = _row("Xoryn's Masterpiece", description, "max_magicka")
    stamina = _row("Xoryn's Masterpiece", description, "max_stamina")

    assert magicka.reviewed_delta == 1667.0
    assert stamina.reviewed_delta == 1667.0
    assert magicka.mechanic_complete is True
    assert stamina.mechanic_complete is True


def test_percentage_max_resource_condition_remains_unresolved() -> None:
    row = _row(
        "Armor Master",
        "(5 items) While you have an Armor ability slotted, your Max Health is increased by 5%. "
        "When you use an Armor ability while in combat, your Physical and Spell Resistance is "
        "increased by 138-5940 for 10 seconds.",
        "max_health",
    )

    assert row.mechanic_complete is False
    assert row.unresolved
