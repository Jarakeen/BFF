from __future__ import annotations

import sqlite3

import pytest

from services.encounter_capability_candidate_audit import EncounterCapabilityCandidateAudit


def _make_db(path, *, with_description: bool = True) -> None:
    with sqlite3.connect(path) as db:
        if with_description:
            db.executescript(
                """
                CREATE TABLE ability (
                    ability_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    base_ability_id INTEGER,
                    morph INTEGER,
                    rank INTEGER,
                    class_type TEXT,
                    skill_line TEXT,
                    description TEXT
                );
                """
            )
            db.executemany(
                """
                INSERT INTO ability(
                    ability_id, name, base_ability_id, morph, rank,
                    class_type, skill_line, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (1, "Quiet Skill", 100, 0, 4, "Templar", "Restoring Light", "Remove negative effects from allies."),
                    (2, "Purge", 200, 1, 4, "", "Support", "Does something useful."),
                    (3, "Ordinary Skill", 300, 0, 4, "", "Weapon", "No relevant mechanic here."),
                    (4, "Interrupting Shot", 400, 2, 4, "", "Bow", "Interrupts a target."),
                ),
            )
        else:
            db.executescript(
                """
                CREATE TABLE ability (
                    ability_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                );
                """
            )
            db.executemany(
                "INSERT INTO ability(ability_id, name) VALUES (?, ?)",
                ((1, "Efficient Purge"), (2, "Ordinary Skill")),
            )


def test_cleanse_candidates_search_available_source_fields_without_promoting_truth(tmp_path):
    database = tmp_path / "eso.db"
    _make_db(database)

    rows = EncounterCapabilityCandidateAudit(database).candidates("cleanse")

    assert [(row.ability_id, row.matched_field) for row in rows] == [
        (1, "description"),
        (2, "name"),
    ]
    assert rows[0].base_ability_id == 100
    assert rows[0].morph == 0
    assert rows[0].rank == 4
    assert rows[0].class_type == "Templar"
    assert rows[0].skill_line == "Restoring Light"
    assert rows[0].matched_source_text == "Remove negative effects from allies."
    assert rows[1].matched_source_text == "Purge"
    # Minimal fixture has no effect-link schema; discovery therefore reports
    # candidates without fabricating an EffectVariant identity.
    assert all(row.resolved_effect_names == () for row in rows)


def test_candidate_audit_degrades_to_name_only_when_description_and_metadata_columns_are_absent(tmp_path):
    database = tmp_path / "eso.db"
    _make_db(database, with_description=False)

    rows = EncounterCapabilityCandidateAudit(database).candidates("cleanse")

    assert len(rows) == 1
    assert rows[0].ability_name == "Efficient Purge"
    assert rows[0].matched_field == "name"
    assert rows[0].matched_source_text == "Efficient Purge"
    assert rows[0].base_ability_id is None
    assert rows[0].morph is None
    assert rows[0].rank is None
    assert rows[0].class_type == ""
    assert rows[0].skill_line == ""


def test_interrupt_discovery_is_separate_from_cleanse(tmp_path):
    database = tmp_path / "eso.db"
    _make_db(database)
    audit = EncounterCapabilityCandidateAudit(database)

    interrupt = audit.candidates("interrupt")
    cleanse = audit.candidates("cleanse")

    assert {row.ability_id for row in interrupt} == {4}
    assert {row.ability_id for row in cleanse} == {1, 2}
    assert interrupt[0].base_ability_id == 400
    assert interrupt[0].morph == 2
    assert interrupt[0].matched_source_text == "Interrupts a target."


def test_unknown_capability_type_is_rejected(tmp_path):
    database = tmp_path / "eso.db"
    _make_db(database)

    with pytest.raises(ValueError, match="Unsupported capability_type"):
        EncounterCapabilityCandidateAudit(database).candidates("dodge")


def test_missing_database_is_explicit(tmp_path):
    with pytest.raises(FileNotFoundError):
        EncounterCapabilityCandidateAudit(tmp_path / "missing.db").candidates("cleanse")
