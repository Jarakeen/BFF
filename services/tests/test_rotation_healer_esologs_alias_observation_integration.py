import json
import sqlite3

from services.rotation_healer_esologs_observation_extractor import (
    RotationHealerEsoLogsObservationExtractor,
    RotationHealerEsoLogsObservationTarget,
)


def _database(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                base_ability_id INTEGER NOT NULL,
                name TEXT
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER NOT NULL,
                ability_id INTEGER NOT NULL,
                raw_name TEXT,
                rank INTEGER,
                morph INTEGER
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT,
                index_name TEXT,
                coef_description TEXT,
                duration REAL
            );
            CREATE TABLE skill_coefficient (
                skill_rank_id INTEGER NOT NULL,
                coefficient_number INTEGER NOT NULL,
                type TEXT,
                a REAL,
                b REAL,
                c REAL,
                r REAL,
                avg REAL
            );
            """
        )
        db.execute(
            "INSERT INTO skill(id, base_ability_id, name) VALUES (1, 93807, 'Budding Seeds')"
        )
        db.execute(
            """
            INSERT INTO skill_rank(id, skill_id, ability_id, raw_name, rank, morph)
            VALUES (6910, 1, 93807, 'Budding Seeds', 4, 1)
            """
        )
        db.executemany(
            "INSERT INTO ability(ability_id, name, index_name, coef_description, duration) VALUES (?, ?, ?, ?, ?)",
            (
                (
                    93807,
                    "Budding Seeds",
                    "budding_seeds",
                    "While the field grows, you and allies are healed for $2 Health every 1 second.",
                    6000,
                ),
                (
                    193807,
                    "Budding Seeds periodic alias",
                    "budding_seeds",
                    "",
                    6000,
                ),
            ),
        )
        db.execute(
            """
            INSERT INTO skill_coefficient(
                skill_rank_id, coefficient_number, type, a, b, c, r, avg
            ) VALUES (6910, 2, '8', 0.1, 1.0, 0.0, 1.0, NULL)
            """
        )
    return path


def _raw(tmp_path):
    path = tmp_path / "raw.json"
    events = [
        {
            "timestamp": 10000,
            "type": "cast",
            "sourceID": 7,
            "targetID": 20,
            "sourceIsFriendly": True,
            "targetIsFriendly": True,
            "abilityGameID": 193807,
            "ability": {"name": "Budding Seeds"},
            "castTrackID": 10,
        },
    ]
    for timestamp in (11000, 12000, 13000, 14000, 15000, 16000):
        events.append(
            {
                "timestamp": timestamp,
                "type": "hot",
                "sourceID": 7,
                "targetID": 21,
                "sourceIsFriendly": True,
                "targetIsFriendly": True,
                "abilityGameID": 193807,
                "ability": {"name": "Budding Seeds"},
                "tick": True,
            }
        )
    payload = {
        "report_code": "ABC123",
        "fights": {
            "4": {
                "metadata": {"id": 4, "name": "Test Fight"},
                "events": events,
                "event_count": len(events),
            }
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_extraction_matches_numeric_alias_from_canonical_skill_identity(tmp_path):
    extractor = RotationHealerEsoLogsObservationExtractor(_database(tmp_path))
    target = RotationHealerEsoLogsObservationTarget(
        "Budding Seeds",
        2,
        93807,
        "budding_seeds",
    )

    assert extractor.ability_ids_for_target(target) == (93807, 193807)

    report = extractor.extract(
        _raw(tmp_path),
        fight_id=4,
        caster_id=7,
        targets=(target,),
    )

    assert report.unresolved == ()
    assert len(report.candidates) == 1
    candidate = report.candidates[0]
    assert candidate.observed_ability_game_id == 193807
    assert candidate.sample.observed_tick_times_seconds == (
        11.0,
        12.0,
        13.0,
        14.0,
        15.0,
        16.0,
    )
    payload = report.to_candidate_fixture_payload()
    assert payload["samples"][0]["candidate_metadata"]["canonical_skill_id"] == "budding_seeds"
    assert payload["samples"][0]["candidate_metadata"]["ability_game_id"] == 193807
