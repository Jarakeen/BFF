import json
import sqlite3

from importers.champion_point_importer import ChampionPointSkillImporter


def _database(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill (
            id INTEGER PRIMARY KEY,
            name TEXT,
            index_name TEXT,
            base_ability_id INTEGER
        );
        CREATE TABLE skill_rank (
            id INTEGER PRIMARY KEY,
            skill_id INTEGER,
            ability_id INTEGER
        );
        CREATE TABLE champion_point (
            id INTEGER PRIMARY KEY,
            name TEXT,
            ability_id INTEGER,
            skill_id INTEGER,
            discipline_index INTEGER
        );
        INSERT INTO skill VALUES (10, 'Necrotic Orb', 'Necrotic Orb', 42027);
        INSERT INTO skill_rank VALUES (100, 10, 42028);
        INSERT INTO champion_point VALUES
            (1, 'Rejuvenator', 1, 1, 1),
            (2, 'Soothing Tide', 2, 2, 1),
            (3, 'Swift Renewal', 3, 3, 1);
        """
    )
    db.commit()
    db.close()


def test_importer_consumes_legacy_base_skill_output_and_preserves_conditions(tmp_path):
    database = tmp_path / 'eso.db'
    source = tmp_path / 'skill_champion_points.json'
    _database(database)
    source.write_text(
        json.dumps(
            {
                'source': 'ESO-Hub',
                'skills': [
                    {
                        'skill_id': 10,
                        'skill_name': 'Necrotic Orb',
                        'url': 'https://eso-hub.com/en/skills/guild/undaunted/necrotic-orb',
                        'champion_points': [
                            {
                                'champion_point_name': 'Rejuvenator',
                                'condition': 'only while slotted',
                                'source': 'ESO-Hub',
                            },
                            {
                                'champion_point_name': 'Soothing Tide',
                                'condition': 'only while slotted',
                                'source': 'ESO-Hub',
                            },
                        ],
                    }
                ],
            }
        ),
        encoding='utf-8',
    )

    ChampionPointSkillImporter(database=database, source_file=source).run()

    with sqlite3.connect(database) as db:
        rows = db.execute(
            """
            SELECT cp.name, cps.condition, cps.source, cps.confidence,
                   cps.source_url, cps.raw_source
            FROM champion_point_skill cps
            JOIN champion_point cp ON cp.id = cps.champion_point_id
            ORDER BY cp.name
            """
        ).fetchall()

    assert rows == [
        (
            'Rejuvenator', 'only while slotted', 'ESO-Hub', 'Explicit',
            'https://eso-hub.com/en/skills/guild/undaunted/necrotic-orb',
            'Necrotic Orb -> Rejuvenator (only while slotted)',
        ),
        (
            'Soothing Tide', 'only while slotted', 'ESO-Hub', 'Explicit',
            'https://eso-hub.com/en/skills/guild/undaunted/necrotic-orb',
            'Necrotic Orb -> Soothing Tide (only while slotted)',
        ),
    ]


def test_importer_persists_rank_specific_morph_evidence_separately(tmp_path):
    database = tmp_path / 'eso.db'
    source = tmp_path / 'skill_champion_points.json'
    _database(database)
    source.write_text(
        json.dumps(
            {
                'skills': [
                    {
                        'skill_id': 10,
                        'skill_rank_id': 100,
                        'ability_id': 42028,
                        'skill_name': 'Energy Orb',
                        'url': 'https://eso-hub.com/en/skills/guild/undaunted/energy-orb',
                        'champion_points': [
                            {'champion_point_name': 'Rejuvenator', 'condition': 'only while slotted', 'source': 'ESO-Hub'},
                            {'champion_point_name': 'Soothing Tide', 'condition': 'only while slotted', 'source': 'ESO-Hub'},
                        ],
                    }
                ]
            }
        ),
        encoding='utf-8',
    )

    ChampionPointSkillImporter(database=database, source_file=source).run()

    with sqlite3.connect(database) as db:
        ranked = db.execute(
            """
            SELECT cp.name, cps.skill_rank_id, cps.skill_id, cps.ability_id, cps.condition
            FROM champion_point_skill_rank cps
            JOIN champion_point cp ON cp.id = cps.champion_point_id
            ORDER BY cp.name
            """
        ).fetchall()
        legacy_count = db.execute("SELECT COUNT(*) FROM champion_point_skill").fetchone()[0]

    assert ranked == [
        ('Rejuvenator', 100, 10, 42028, 'only while slotted'),
        ('Soothing Tide', 100, 10, 42028, 'only while slotted'),
    ]
    assert legacy_count == 0


def test_importer_does_not_create_unharvested_relationship(tmp_path):
    database = tmp_path / 'eso.db'
    source = tmp_path / 'skill_champion_points.json'
    _database(database)
    source.write_text(
        json.dumps(
            {
                'skills': [
                    {
                        'skill_id': 10,
                        'skill_name': 'Necrotic Orb',
                        'champion_points': [
                            {'champion_point_name': 'Rejuvenator', 'source': 'ESO-Hub'}
                        ],
                    }
                ]
            }
        ),
        encoding='utf-8',
    )

    ChampionPointSkillImporter(database=database, source_file=source).run()

    with sqlite3.connect(database) as db:
        linked = {
            row[0]
            for row in db.execute(
                """
                SELECT cp.name
                FROM champion_point_skill cps
                JOIN champion_point cp ON cp.id = cps.champion_point_id
                """
            ).fetchall()
        }

    assert linked == {'Rejuvenator'}
    assert 'Swift Renewal' not in linked
