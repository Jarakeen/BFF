import sqlite3

from minmax.skill_component_condition import SkillComponentConditionType
from minmax.skill_component_condition_repository import SkillComponentConditionRepository


def _make_db(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (
            id INTEGER PRIMARY KEY,
            ability_id INTEGER NOT NULL
        );
        CREATE TABLE ability (
            ability_id INTEGER PRIMARY KEY,
            coef_description TEXT
        );

        INSERT INTO skill_rank VALUES (10, 100);
        INSERT INTO ability VALUES (
            100,
            'Deal $1 Magic Damage to an enemy below 25% Health.'
        );
        """
    )
    db.commit()
    db.close()


def test_repository_resolves_explicit_health_threshold(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    conditions = SkillComponentConditionRepository(path).resolve(10, 1)

    assert len(conditions) == 1
    condition = conditions[0]
    assert condition.condition_type is SkillComponentConditionType.TARGET_HEALTH_BELOW_PERCENT
    assert condition.threshold == 0.25


def test_repository_returns_empty_for_unknown_rank(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    assert SkillComponentConditionRepository(path).resolve(999, 1) == ()


def test_repository_does_not_borrow_missing_component_text(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    assert SkillComponentConditionRepository(path).resolve(10, 2) == ()


def test_repository_fails_closed_when_required_tables_are_missing(tmp_path):
    path = tmp_path / "eso.db"
    sqlite3.connect(path).close()

    assert SkillComponentConditionRepository(path).resolve(10, 1) == ()


def _make_ordinal_db(path, threshold_text):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL);
        CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT);
        INSERT INTO skill_rank VALUES (20, 200);
        """
    )
    db.execute(
        "INSERT INTO ability VALUES (?, ?)",
        (
            200,
            "Deal $1 Physical Damage and $2 Bleed Damage. The second hit deals up to 125% more damage to enemies with "
            + threshold_text
            + " Health and heals you for $3 Health.",
        ),
    )
    db.commit()
    db.close()


def test_repository_prefers_explicit_second_hit_over_nearby_third_placeholder(tmp_path):
    path = tmp_path / "eso.db"
    _make_ordinal_db(path, "less than 25%")

    repository = SkillComponentConditionRepository(path)
    second = repository.resolve(20, 2)
    third = repository.resolve(20, 3)

    assert len(second) == 1
    assert second[0].threshold == 0.25
    assert third == ()


def test_repository_normalizes_joined_less_than_for_ordinal_owner(tmp_path):
    path = tmp_path / "eso.db"
    _make_ordinal_db(path, "lessthan 25%")

    repository = SkillComponentConditionRepository(path)
    second = repository.resolve(20, 2)
    third = repository.resolve(20, 3)

    assert len(second) == 1
    assert second[0].threshold == 0.25
    assert third == ()
