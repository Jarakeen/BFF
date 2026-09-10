from __future__ import annotations

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
            "INSERT INTO skill(id, base_ability_id, name) VALUES (1, 85840, 'Budding Seeds')"
        )
        db.execute(
            """
            INSERT INTO skill_rank(id, skill_id, ability_id, raw_name, rank, morph)
            VALUES (6910, 1, 85840, 'Budding Seeds', 4, 1)
            """
        )
        db.execute(
            """
            INSERT INTO ability(ability_id, name, index_name, coef_description, duration)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                85840,
                "Budding Seeds",
                "Budding Seeds",
                "Summon a field which blooms after 6 seconds, healing for $1 Health. "
                "While the field grows, you and allies are healed for $2 Health every 1 second.",
                6000,
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


def _event(timestamp, event_type, *, ability, target=20, tick=None):
    event = {
        "timestamp": timestamp,
        "type": event_type,
        "sourceID": 7,
        "targetID": target,
        "sourceIsFriendly": True,
        "targetIsFriendly": True,
        "abilityGameID": ability,
    }
    if tick is not None:
        event["tick"] = tick
    return event


def test_extractor_uses_canonical_cast_alias_and_reviewed_periodic_effect_alias(tmp_path):
    events = [_event(10000, "cast", ability=85840)]
    for timestamp in (11000, 12000, 13000, 14000, 15000, 16000):
        events.append(_event(timestamp, "hot", ability=129434, target=21, tick=True))
        events.append(_event(timestamp, "hot", ability=129434, target=22, tick=True))
    # A distinct Budding Seeds-related direct/bloom-looking ID must not leak into
    # the coefficient-2 periodic stream merely because it occurs in the window.
    events.append(_event(16000, "heal", ability=85841, target=21, tick=False))

    raw = tmp_path / "raw.json"
    raw.write_text(
        json.dumps(
            {
                "report_code": "ABC123",
                "fights": {
                    "4": {
                        "metadata": {"id": 4, "name": "Test Fight"},
                        "events": events,
                        "event_count": len(events),
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    target = RotationHealerEsoLogsObservationTarget(
        source_name="Budding Seeds",
        coefficient_number=2,
        ability_game_id=93807,
        canonical_skill_id="budding_seeds",
    )
    extractor = RotationHealerEsoLogsObservationExtractor(_database(tmp_path))

    assert extractor.ability_ids_for_target(target) == (85840,)
    assert extractor.periodic_effect_ids_for_target(target) == (129434,)

    report = extractor.extract(
        raw,
        fight_id=4,
        caster_id=7,
        targets=(target,),
    )

    assert report.unresolved == ()
    assert len(report.candidates) == 1
    candidate = report.candidates[0]
    assert candidate.observed_ability_game_id == 85840
    assert candidate.raw_periodic_heal_event_count == 12
    assert candidate.sample.observed_tick_times_seconds == (
        11.0,
        12.0,
        13.0,
        14.0,
        15.0,
        16.0,
    )
    assert any("periodicEffectAliases=(129434,)" in item for item in candidate.sample.provenance)
