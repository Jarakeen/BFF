from __future__ import annotations

import sqlite3

import pytest

from services.encounter_capability_candidate_audit import EncounterCapabilityCandidateAudit


def _make_db(path, *, with_description: bool = True) -> None:
    with sqlite3.connect(path) as db:
        description = ", description TEXT" if with_description else ""
        db.executescript(
            f"""
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
                {description}
            );
            """
        )
        if with_description:
            db.executemany(
                "INSERT INTO ability(ability_id, name, description) VALUES (?, ?, ?)",
                (
                    (1, "Quiet Skill", "Remove negative effects from allies."),
                    (2, "Purge", "Does something useful."),
                    (3, "Ordinary Skill", "No relevant mechanic here."),
                    (4, "Interrupting Shot", "Interrupts a target."),
                ),
            )
        else:
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
    # Minimal fixture has no effect-link schema; discovery therefore reports
    # candidates without fabricating an EffectVariant identity.
    assert all(row.resolved_effect_names == () for row in rows)


def test_candidate_audit_degrades_to_name_only_when_description_columns_are_absent(tmp_path):
    database = tmp_path / "eso.db"
    _make_db(database, with_description=False)

    rows = EncounterCapabilityCandidateAudit(database).candidates("cleanse")

    assert len(rows) == 1
    assert rows[0].ability_name == "Efficient Purge"
    assert rows[0].matched_field == "name"


def test_interrupt_discovery_is_separate_from_cleanse(tmp_path):
    database = tmp_path / "eso.db"
    _make_db(database)
    audit = EncounterCapabilityCandidateAudit(database)

    interrupt = audit.candidates("interrupt")
    cleanse = audit.candidates("cleanse")

    assert {row.ability_id for row in interrupt} == {4}
    assert {row.ability_id for row in cleanse} == {1, 2}


def test_unknown_capability_type_is_rejected(tmp_path):
    database = tmp_path / "eso.db"
    _make_db(database)

    with pytest.raises(ValueError, match="Unsupported capability_type"):
        EncounterCapabilityCandidateAudit(database).candidates("dodge")


def test_missing_database_is_explicit(tmp_path):
    with pytest.raises(FileNotFoundError):
        EncounterCapabilityCandidateAudit(tmp_path / "missing.db").candidates("cleanse")
