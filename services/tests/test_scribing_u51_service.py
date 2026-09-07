from __future__ import annotations

import sqlite3

from services.scribing_u51_service import U51ScribingService


def _database(path):
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE scribing_u51_source (
                source_key TEXT PRIMARY KEY,
                game_update INTEGER,
                channel TEXT,
                scripts_record TEXT,
                skills_record TEXT,
                descriptions_record TEXT,
                scripts_sha256 TEXT,
                skills_sha256 TEXT,
                descriptions_sha256 TEXT,
                imported_at TEXT
            );
            CREATE TABLE scribing_u51_script (
                source_key TEXT,
                script_id INTEGER,
                slot INTEGER,
                script_type TEXT,
                name TEXT,
                description TEXT,
                hint TEXT,
                icon TEXT
            );
            CREATE TABLE scribing_u51_crafted_skill (
                source_key TEXT,
                crafted_ability_id INTEGER,
                ability_id INTEGER,
                skill_type INTEGER,
                name TEXT,
                description TEXT,
                hint TEXT,
                icon TEXT
            );
            CREATE TABLE scribing_u51_skill_script (
                source_key TEXT,
                crafted_ability_id INTEGER,
                script_id INTEGER,
                slot INTEGER
            );
            CREATE TABLE scribing_crafted_script_description (
                source_key TEXT,
                source_row_id INTEGER,
                crafted_ability_id INTEGER,
                script_id INTEGER,
                class_id INTEGER,
                ability_id INTEGER,
                name TEXT,
                description_raw TEXT,
                description TEXT
            );
            """
        )
        source = U51ScribingService.SOURCE_KEY
        description_source = U51ScribingService.DESCRIPTION_SOURCE_KEY
        connection.execute(
            "INSERT INTO scribing_u51_source VALUES (?,51,'PTS','','','','','','','')",
            (source,),
        )
        connection.execute(
            "INSERT INTO scribing_u51_crafted_skill VALUES (?,?,?,?,?,?,?,?)",
            (source, 8, 217462, 4, 'Soul Burst', 'Burst', '', '/esoui/art/icons/grimoire_soulmagic2.dds'),
        )
        for script_id, slot, name in (
            (20, 1, 'Damage Shield'),
            (24, 2, "Assassin's Misery"),
            (55, 3, 'Courage'),
        ):
            connection.execute(
                "INSERT INTO scribing_u51_script VALUES (?,?,?,?,?,?,?,?)",
                (source, script_id, slot, {1:'focus',2:'signature',3:'affix'}[slot], name, '', '', ''),
            )
            connection.execute(
                "INSERT INTO scribing_u51_skill_script VALUES (?,?,?,?)",
                (source, 8, script_id, slot),
            )
        rows = (
            (1, 20, 0, 222370, 'Warding Burst', 'Grants a 4000 damage shield.'),
            (2, 24, 0, 222370, 'Warding Burst', 'Applies status effects.'),
            (3, 55, 0, 222370, 'Warding Burst', 'Grants Minor Courage.'),
        )
        for row_id, script_id, class_id, ability_id, name, description in rows:
            connection.execute(
                "INSERT INTO scribing_crafted_script_description VALUES (?,?,?,?,?,?,?,?,?)",
                (description_source, row_id, 8, script_id, class_id, ability_id, name, description, description),
            )
        connection.commit()


def test_u51_service_resolves_catalog_choices_and_result(tmp_path):
    path = tmp_path / 'eso.db'
    _database(path)
    service = U51ScribingService(path)

    assert service.available is True
    assert service.grimoire_names() == ['Soul Burst']
    assert service.compatible_focus('Soul Burst') == ['Damage Shield']
    assert service.compatible_signature('Soul Burst') == ["Assassin's Misery"]
    assert service.compatible_affix('Soul Burst') == ['Courage']
    assert service.result_name('Soul Burst', 'Damage Shield') == 'Warding Burst'
    assert service.result_ability_id('Soul Burst', 'Damage Shield') == 222370


def test_u51_service_combines_clean_resolved_descriptions(tmp_path):
    path = tmp_path / 'eso.db'
    _database(path)
    service = U51ScribingService(path)

    detail = service.combined_description(
        'Soul Burst',
        'Damage Shield',
        "Assassin's Misery",
        'Courage',
    )

    assert 'Focus: Grants a 4000 damage shield.' in detail
    assert "Signature: Applies status effects." in detail
    assert 'Affix: Grants Minor Courage.' in detail
