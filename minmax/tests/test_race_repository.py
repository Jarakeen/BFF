from pathlib import Path

from minmax.race_repository import RaceRepository


DB_PATH = Path("data/eso.db")

ALTMER_ID = 1


def repository() -> RaceRepository:
    return RaceRepository(DB_PATH)


def test_get_race_by_id():
    race = repository().get_race_by_id(ALTMER_ID)

    assert race is not None
    assert race.id == ALTMER_ID
    assert race.name == "Altmer"
    assert race.alliance == "Aldmeri Dominion"
    assert race.association == "Destruction Staff"


def test_get_race_by_name():
    race = repository().get_race("Altmer")

    assert race is not None
    assert race.id == ALTMER_ID


def test_unknown_race_returns_none():
    assert repository().get_race_by_id(999999) is None


def test_get_racial_stats():
    stats = repository().get_stats(ALTMER_ID)

    assert [
        (stat.stat, stat.value)
        for stat in stats
    ] == [
        ("max_magicka", 2000),
        ("spell_damage", 258),
        ("weapon_damage", 258),
    ]


def test_get_stat_map():
    assert repository().get_stat_map(ALTMER_ID) == {
        "max_magicka": 2000.0,
        "spell_damage": 258.0,
        "weapon_damage": 258.0,
    }


def test_get_stat_map_by_name():
    assert repository().get_stat_map_by_name("Altmer")["max_magicka"] == 2000.0
    assert repository().get_stat_map_by_name("Not A Race") == {}
