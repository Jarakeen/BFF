from pathlib import Path
import json
import sqlite3

from tools.audit_phase13_xalvakka_cross_lane_add_taunt_transitions import audit, observe


def _write_lane_assignment(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "assignments": [
                    {
                        "encounter_id": "xalvakka",
                        "report_code": "XVMgLdq6GpQ7bhKN",
                        "evidence_scope": "single_report_reviewed_observed_lane_assignment",
                        "taunt_state_effect_id": 38254,
                        "fights": [30],
                        "interpretation": "fixture",
                        "lanes": [
                            {
                                "lane_id": "boss_holder",
                                "source_id": 5,
                                "character_name": "Dualtalons",
                                "account_name": "@Cerberuss123",
                                "actor_type": "Arcanist",
                                "eso_logs_role": "tank",
                                "role_fights": 1,
                                "boss_taunt_events": 10,
                                "boss_fights": 1,
                                "add_taunt_events": 2,
                                "add_instances": 1,
                                "interpretation": "fixture",
                            },
                            {
                                "lane_id": "add_handler",
                                "source_id": 1,
                                "character_name": "Fulcinator",
                                "account_name": "@FulciLives",
                                "actor_type": "DragonKnight",
                                "eso_logs_role": "tank",
                                "role_fights": 1,
                                "boss_taunt_events": 2,
                                "boss_fights": 1,
                                "add_taunt_events": 10,
                                "add_instances": 1,
                                "interpretation": "fixture",
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _db(path: Path) -> None:
    db = sqlite3.connect(path)
    try:
        db.executescript(
            """
            CREATE TABLE log_report_actor (
                report_code TEXT,
                actor_id INTEGER,
                name TEXT
            );
            CREATE TABLE log_event (
                report_code TEXT,
                fight_id INTEGER,
                event_index INTEGER,
                timestamp REAL,
                event_type TEXT,
                source_id INTEGER,
                target_id INTEGER,
                target_instance INTEGER,
                ability_game_id INTEGER,
                raw_json TEXT
            );
            """
        )
        db.execute(
            "INSERT INTO log_report_actor(report_code, actor_id, name) VALUES (?, ?, ?)",
            ("XVMgLdq6GpQ7bhKN", 104, "Iron Atronach"),
        )
        events = [
            # add_handler owns first interval 1s -> 11s
            (0, 1000, "applydebuff", 1),
            (1, 11000, "removedebuff", 1),
            # boss_holder begins 1s later: sequential transition
            (2, 12000, "applydebuff", 5),
            (3, 20000, "removedebuff", 5),
            # add_handler reapplies before boss_holder's second interval ends: overlap
            (4, 30000, "applydebuff", 5),
            (5, 33000, "applydebuff", 1),
            (6, 36000, "removedebuff", 1),
            (7, 40000, "removedebuff", 5),
        ]
        for event_index, timestamp, event_type, source_id in events:
            db.execute(
                """
                INSERT INTO log_event(
                    report_code, fight_id, event_index, timestamp, event_type,
                    source_id, target_id, target_instance, ability_game_id, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "XVMgLdq6GpQ7bhKN",
                    30,
                    event_index,
                    timestamp,
                    event_type,
                    source_id,
                    104,
                    1,
                    38254,
                    json.dumps({"targetInstance": 1}),
                ),
            )
        db.commit()
    finally:
        db.close()


def test_cross_lane_audit_reports_sequential_and_overlap(monkeypatch, tmp_path: Path) -> None:
    from services import rotation_tank_observed_lane_assignment_service as lane_module
    from tools import audit_phase13_xalvakka_cross_lane_add_taunt_transitions as audit_module

    reviewed = tmp_path / "reviewed.json"
    database = tmp_path / "runtime.db"
    _write_lane_assignment(reviewed)
    _db(database)

    class _FixtureService(lane_module.RotationTankObservedLaneAssignmentService):
        def __init__(self):
            super().__init__(reviewed)

    monkeypatch.setattr(audit_module, "RotationTankObservedLaneAssignmentService", _FixtureService)

    rows = observe(database)
    assert any(
        row.relation == "sequential"
        and row.from_lane == "add_handler"
        and row.to_lane == "boss_holder"
        and row.delta_ms == 1000.0
        for row in rows
    )
    assert any(
        row.relation == "overlap"
        and row.from_lane == "boss_holder"
        and row.to_lane == "add_handler"
        and row.delta_ms == -7000.0
        for row in rows
    )

    output = "\n".join(audit(database))
    assert "PHASE 13 XALVAKKA CROSS-LANE ADD TAUNT TRANSITION AUDIT" in output
    assert "actor=Iron Atronach" in output
    assert "no handoff threshold or universal tank-swap policy is promoted" in output
