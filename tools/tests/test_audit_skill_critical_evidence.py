import json
import sqlite3

from tools.audit_skill_critical_evidence import (
    load_critical_evidence,
    summarize_key_paths,
)


def _make_db(path):
    db = sqlite3.connect(path)
    db.execute(
        """
        CREATE TABLE ability (
            ability_id INTEGER PRIMARY KEY,
            name TEXT,
            raw_json TEXT
        )
        """
    )
    rows = [
        (
            100,
            "Explicit Crit Flag",
            json.dumps({"id": 100, "canCrit": True, "nested": {"criticalType": 2}}),
        ),
        (
            200,
            "Prose Only",
            json.dumps({"description": "Gain Critical Chance while active."}),
        ),
        (
            300,
            "Nested Flag",
            json.dumps({"effects": [{"isCriticalAllowed": False}]}),
        ),
        (400, "Broken", "{not valid json"),
        (500, "Missing", None),
    ]
    db.executemany("INSERT INTO ability VALUES (?, ?, ?)", rows)
    db.commit()
    db.close()


def test_critical_evidence_audit_matches_key_names_not_prose_values(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    summary = load_critical_evidence(path)

    assert summary.abilities_scanned == 5
    assert summary.raw_json_present == 4
    assert summary.invalid_json == 1

    key_paths = {hit.key_path for hit in summary.key_hits}
    assert key_paths == {
        "canCrit",
        "nested.criticalType",
        "effects[0].isCriticalAllowed",
    }
    assert all(hit.ability_id != 200 for hit in summary.key_hits)


def test_critical_evidence_summary_preserves_key_value_distribution(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    counts = summarize_key_paths(load_critical_evidence(path).key_hits)

    assert counts[("canCrit", "True")] == 1
    assert counts[("nested.criticalType", "2")] == 1
    assert counts[("effects[0].isCriticalAllowed", "False")] == 1


def test_critical_evidence_limit_applies_to_ability_rows(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)

    summary = load_critical_evidence(path, limit=1)

    assert summary.abilities_scanned == 1
    assert {hit.key_path for hit in summary.key_hits} == {
        "canCrit",
        "nested.criticalType",
    }
