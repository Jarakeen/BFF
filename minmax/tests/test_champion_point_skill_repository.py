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
            skill_id INTEGER,
            ability_id INTEGER
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
        CREATE TABLE champion_point_skill_rank (
            id INTEGER PRIMARY KEY,
            champion_point_id INTEGER NOT NULL,
            skill_rank_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            ability_id INTEGER,
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
        INSERT INTO skill VALUES (10, 'Necrotic Orb');
        INSERT INTO skill_rank VALUES
            (100, 10, 42028),
            (101, 10, 42029);
        INSERT INTO champion_point_skill VALUES
            (1, 3, 10, 'Buffs', NULL, 'ESO-Hub', 'Explicit',
             'https://eso-hub.com/en/skills/guild/undaunted/necrotic-orb',
             'Necrotic Orb -> Swift Renewal');
        INSERT INTO champion_point_skill_rank VALUES
            (1, 1, 100, 10, 42028, 'Buffs', 'only while slotted', 'ESO-Hub', 'Explicit',
             'https://eso-hub.com/en/skills/guild/undaunted/energy-orb',
             'Energy Orb -> Rejuvenator (only while slotted)'),
            (2, 2, 100, 10, 42028, 'Buffs', 'only while slotted', 'ESO-Hub', 'Explicit',
             'https://eso-hub.com/en/skills/guild/undaunted/energy-orb',
             'Energy Orb -> Soothing Tide (only while slotted)');
        """
    )
    db.commit()
    db.close()


def test_repository_returns_legacy_base_skill_metadata(tmp_path):
    path = tmp_path / 'eso.db'
    _db(path)

    rows = ChampionPointSkillRepository(path).get_for_skill_id(10)

    assert [row.champion_point_name for row in rows] == ['Swift Renewal']
    assert rows[0].skill_rank_id is None


def test_repository_prefers_rank_specific_relationships(tmp_path):
    path = tmp_path / 'eso.db'
    _db(path)

    rows = ChampionPointSkillRepository(path).get_for_skill_rank(100)

    assert [row.champion_point_name for row in rows] == ['Rejuvenator', 'Soothing Tide']
    assert rows[0].skill_rank_id == 100
    assert rows[0].ability_id == 42028
    assert rows[0].condition == 'only while slotted'
    assert rows[0].source_url.endswith('/energy-orb')


def test_other_morph_falls_back_only_when_no_rank_specific_rows_exist(tmp_path):
    path = tmp_path / 'eso.db'
    _db(path)

    rows = ChampionPointSkillRepository(path).get_for_skill_rank(101)

    assert [row.champion_point_name for row in rows] == ['Swift Renewal']
    assert rows[0].skill_rank_id is None


def test_rank_specific_hard_gate_rejects_unlisted_cp(tmp_path):
    path = tmp_path / 'eso.db'
    _db(path)
    repo = ChampionPointSkillRepository(path)

    assert repo.explicitly_applies_to_rank(skill_rank_id=100, champion_point_name='Rejuvenator') is True
    assert repo.explicitly_applies_to_rank(skill_rank_id=100, champion_point_name='Soothing Tide') is True
    assert repo.explicitly_applies_to_rank(skill_rank_id=100, champion_point_name='Swift Renewal') is False


def test_missing_relationship_tables_fail_closed(tmp_path):
    path = tmp_path / 'eso.db'
    sqlite3.connect(path).close()
    repo = ChampionPointSkillRepository(path)

    assert repo.available() is False
    assert repo.get_for_skill_id(10) == ()
    assert repo.get_for_skill_rank(100) == ()
    assert repo.explicitly_applies(skill_id=10, champion_point_name='Rejuvenator') is False


def test_relationship_results_are_cached_per_repository_instance(tmp_path):
    path = tmp_path / 'eso.db'
    _db(path)
    repo = ChampionPointSkillRepository(path)

    first_rank = repo.get_for_skill_rank(100)
    first_base = repo.get_for_skill_id(10)

    db = sqlite3.connect(path)
    db.execute("DELETE FROM champion_point_skill_rank WHERE skill_rank_id = 100")
    db.execute("DELETE FROM champion_point_skill WHERE skill_id = 10")
    db.commit()
    db.close()

    assert repo.get_for_skill_rank(100) == first_rank
    assert repo.get_for_skill_id(10) == first_base
    assert ChampionPointSkillRepository(path).get_for_skill_rank(100) == ()
    assert ChampionPointSkillRepository(path).get_for_skill_id(10) == ()
