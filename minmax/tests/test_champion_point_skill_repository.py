import sqlite3

from minmax.champion_point_skill_repository import ChampionPointSkillRepository


def _db(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE champion_point (
            id INTEGER PRIMARY KEY,
            name TEXT
        );
        CREATE TABLE skill (
            id INTEGER PRIMARY KEY,
            name TEXT
        );
        CREATE TABLE skill_rank (
            id INTEGER PRIMARY KEY,
            skill_id INTEGER
        );
        CREATE TABLE champion_point_skill (
            id INTEGER PRIMARY KEY,
            champion_point_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            relationship TEXT NOT NULL,
            condition TEXT,
            source TEXT,
            confidence TEXT,
            source_url TEXT,
            raw_source TEXT
        );
        INSERT INTO champion_point VALUES
            (1, 'Rejuvenator'),
            (2, 'Soothing Tide'),
            (3, 'Swift Renewal');
        INSERT INTO skill VALUES (10, 'Energy Orb');
        INSERT INTO skill_rank VALUES (100, 10);
        INSERT INTO champion_point_skill VALUES
            (1, 1, 10, 'Buffs', 'only while slotted', 'ESO-Hub', 'Explicit',
             'https://eso-hub.com/en/skills/guild/undaunted/energy-orb',
             'Energy Orb -> Rejuvenator (only while slotted)'),
            (2, 2, 10, 'Buffs', 'only while slotted', 'ESO-Hub', 'Explicit',
             'https://eso-hub.com/en/skills/guild/undaunted/energy-orb',
             'Energy Orb -> Soothing Tide (only while slotted)');
        """
    )
    db.commit()
    db.close()


def test_repository_returns_explicit_relationship_metadata(tmp_path):
    path = tmp_path / 'eso.db'
    _db(path)

    rows = ChampionPointSkillRepository(path).get_for_skill_id(10)

    assert [row.champion_point_name for row in rows] == ['Rejuvenator', 'Soothing Tide']
    assert rows[0].condition == 'only while slotted'
    assert rows[0].source == 'ESO-Hub'
    assert rows[0].confidence == 'Explicit'
    assert rows[0].source_url.endswith('/energy-orb')


def test_repository_uses_explicit_link_as_hard_gate(tmp_path):
    path = tmp_path / 'eso.db'
    _db(path)
    repo = ChampionPointSkillRepository(path)

    assert repo.explicitly_applies(skill_id=10, champion_point_name='Rejuvenator') is True
    assert repo.explicitly_applies(skill_id=10, champion_point_name='Soothing Tide') is True
    assert repo.explicitly_applies(skill_id=10, champion_point_name='Swift Renewal') is False


def test_repository_can_resolve_relationships_from_skill_rank(tmp_path):
    path = tmp_path / 'eso.db'
    _db(path)

    rows = ChampionPointSkillRepository(path).get_for_skill_rank(100)

    assert {row.champion_point_name for row in rows} == {'Rejuvenator', 'Soothing Tide'}


def test_missing_relationship_table_fails_closed(tmp_path):
    path = tmp_path / 'eso.db'
    sqlite3.connect(path).close()
    repo = ChampionPointSkillRepository(path)

    assert repo.available() is False
    assert repo.get_for_skill_id(10) == ()
    assert repo.explicitly_applies(skill_id=10, champion_point_name='Rejuvenator') is False
