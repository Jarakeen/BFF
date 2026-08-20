from pathlib import Path

from services.minmax.race_repository import RaceRepository


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