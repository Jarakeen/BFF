from pathlib import Path

from minmax.gear_set_repository import GearSetRepository


DB_PATH = Path("data/eso.db")

VESTMENTS_OF_THE_WARLOCK_ID = 19
WITCHMAN_ARMOR_ID = 20
AKAVIRI_DRAGONGUARD_ID = 21


def test_get_set_by_exact_name():
    repository = GearSetRepository(DB_PATH)

    gear_set = repository.get_set("Vestments of the Warlock")

    assert gear_set is not None
    assert gear_set.id == VESTMENTS_OF_THE_WARLOCK_ID
    assert gear_set.name == "Vestments of the Warlock"


def test_get_set_by_id():
    repository = GearSetRepository(DB_PATH)

    gear_set = repository.get_set_by_id(VESTMENTS_OF_THE_WARLOCK_ID)

    assert gear_set is not None
    assert gear_set.name == "Vestments of the Warlock"


def test_get_set_returns_none_for_unknown_name():
    repository = GearSetRepository(DB_PATH)

    gear_set = repository.get_set("This Set Does Not Exist")

    assert gear_set is None


def test_get_set_by_id_returns_none_for_unknown_id():
    repository = GearSetRepository(DB_PATH)

    gear_set = repository.get_set_by_id(999_999)

    assert gear_set is None


def test_get_bonuses_returns_bonuses_in_piece_count_order():
    repository = GearSetRepository(DB_PATH)

    bonuses = repository.get_bonuses(VESTMENTS_OF_THE_WARLOCK_ID)

    piece_counts = [bonus.piece_count for bonus in bonuses]

    assert piece_counts == sorted(piece_counts)
    assert piece_counts == [2, 3, 4, 5]


def test_get_bonuses_preserves_descriptions_exactly():
    repository = GearSetRepository(DB_PATH)

    bonuses = repository.get_bonuses(VESTMENTS_OF_THE_WARLOCK_ID)

    descriptions = {
        bonus.piece_count: bonus.description
        for bonus in bonuses
    }

    assert descriptions[2] == "(2 items) Adds 3-129 Magicka Recovery"
    assert descriptions[3] == "(3 items) Adds 25-1096 Maximum Magicka"
    assert descriptions[4] == "(4 items) Adds 3-129 Magicka Recovery"
    assert descriptions[5] == (
        "(5 items) When you cast an ability that costs resources while "
        "under |cffffff25|r% Magicka, you restore |cffffff263-11350|r "
        "Magicka. This effect can occur once every |cffffff45|r seconds."
    )


def test_get_bonus_returns_correct_bonus_for_known_piece_count():
    repository = GearSetRepository(DB_PATH)

    bonus = repository.get_bonus(VESTMENTS_OF_THE_WARLOCK_ID, 3)

    assert bonus is not None
    assert bonus.set_id == VESTMENTS_OF_THE_WARLOCK_ID
    assert bonus.piece_count == 3
    assert bonus.description == "(3 items) Adds 25-1096 Maximum Magicka"


def test_get_bonus_returns_none_for_unavailable_piece_count():
    repository = GearSetRepository(DB_PATH)

    bonus = repository.get_bonus(VESTMENTS_OF_THE_WARLOCK_ID, 12)

    assert bonus is None


def test_witchman_armor_set_lookup():
    repository = GearSetRepository(DB_PATH)

    gear_set = repository.get_set_by_id(WITCHMAN_ARMOR_ID)

    assert gear_set is not None
    assert gear_set.name == "Witchman Armor"

    bonuses = repository.get_bonuses(WITCHMAN_ARMOR_ID)

    assert len(bonuses) > 0
    assert all(bonus.set_id == WITCHMAN_ARMOR_ID for bonus in bonuses)


def test_akaviri_dragonguard_set_lookup():
    repository = GearSetRepository(DB_PATH)

    gear_set = repository.get_set_by_id(AKAVIRI_DRAGONGUARD_ID)

    assert gear_set is not None
    assert gear_set.name == "Akaviri Dragonguard"

    bonuses = repository.get_bonuses(AKAVIRI_DRAGONGUARD_ID)

    assert len(bonuses) > 0
    assert all(bonus.set_id == AKAVIRI_DRAGONGUARD_ID for bonus in bonuses)
