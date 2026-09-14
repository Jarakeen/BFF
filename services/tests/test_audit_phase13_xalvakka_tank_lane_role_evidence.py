from pathlib import Path
import sqlite3

from tools.audit_phase13_xalvakka_tank_lane_role_evidence import audit


def _db(path: Path) -> None:
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE log_report_actor (
            report_code TEXT, actor_id INTEGER, name TEXT
        );
        CREATE TABLE log_actor (
            report_code TEXT, fight_id INTEGER, actor_id INTEGER,
            name TEXT, display_name TEXT, actor_type TEXT, role TEXT
        );
        CREATE TABLE log_observed_target (
            report_code TEXT, fight_id INTEGER, target_id INTEGER
        );
        CREATE TABLE log_event (
            report_code TEXT, fight_id INTEGER, event_index INTEGER,
            timestamp REAL, event_type TEXT, source_id INTEGER,
            target_id INTEGER, target_instance INTEGER,
            ability_game_id INTEGER, raw_json TEXT
        );
        """
    )
    db.executemany(
        "INSERT INTO log_report_actor VALUES (?,?,?)",
        [
            ("R", 1, "Fulcinator"),
            ("R", 5, "Dualtalons"),
            ("R", 100, "Xalvakka"),
            ("R", 200, "Iron Atronach"),
            ("R", 201, "Daedroth"),
        ],
    )
    db.executemany(
        "INSERT INTO log_actor VALUES (?,?,?,?,?,?,?)",
        [
            ("R", 30, 1, "Fulcinator", "Fulcinator", "DragonKnight", "tank"),
            ("R", 30, 5, "Dualtalons", "Dualtalons", "Necromancer", "tank"),
        ],
    )
    db.execute("INSERT INTO log_observed_target VALUES ('R',30,100)")
    events = [
        ("R",30,0,1.0,"applydebuff",1,200,1,38254,"{}"),
        ("R",30,1,2.0,"removedebuff",1,200,1,38254,"{}"),
        ("R",30,2,3.0,"applydebuff",5,100,0,38254,"{}"),
        ("R",30,3,4.0,"removedebuff",5,100,0,38254,"{}"),
        ("R",30,4,5.0,"applydebuff",5,201,2,38254,"{}"),
        ("R",30,5,6.0,"removedebuff",5,201,2,38254,"{}"),
    ]
    db.executemany("INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?,?)", events)
    db.commit()
    db.close()


def test_audit_reports_fight_roles_and_boss_vs_add_taunt_ownership(tmp_path: Path) -> None:
    path = tmp_path / "runtime.db"
    _db(path)
    lines = audit(path)
    text = "\n".join(lines)

    assert "OBSERVED_SOURCES=2" in text
    assert "name=Fulcinator roles=[tank=1]" in text
    assert "name=Fulcinator" in text and "boss_taunt_events=0" in text
    assert "name=Dualtalons roles=[tank=1]" in text
    assert "name=Dualtalons" in text and "boss_taunt_events=2" in text
    assert "Iron Atronach=2" in text
    assert "Daedroth=2" in text
    assert "Main/Off Tank promotion still requires" in text
