import sqlite3

from minmax.skill_component_source_alignment_issue import (
    SkillComponentSourceAlignmentIssueType,
)
from minmax.skill_component_source_alignment_issue_repository import (
    SkillComponentSourceAlignmentIssueRepository,
)


def _db(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL);
            CREATE TABLE skill_coefficient (
                skill_rank_id INTEGER NOT NULL,
                coefficient_number INTEGER NOT NULL,
                type TEXT, a REAL, b REAL, c REAL, r REAL, avg REAL
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                type3 TEXT, a3 REAL, b3 REAL, c3 REAL, r3 REAL, avg3 REAL,
                coef_description TEXT, raw_description TEXT
            );
            """
        )
    return path


def test_special_active_slot_with_timing_placeholder_mismatch_is_explicitly_unsupported(tmp_path):
    path = _db(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO skill_rank VALUES (4500, 20930)")
        db.execute(
            "INSERT INTO skill_coefficient VALUES (4500, 3, '-73', 0.00015873, 0.00166667, 50, 1, 0)"
        )
        db.execute(
            "INSERT INTO ability VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                20930,
                "-73",
                0.00015873,
                0.00166667,
                50,
                1,
                0,
                "Deal $1 Flame Damage every 0.5 seconds in a channeled attack over 4.8 seconds.",
                "Deal <<1>> every <<2>> in a channeled attack over <<3>>.",
            ),
        )

    rows = SkillComponentSourceAlignmentIssueRepository(path).resolve(4500, 3)
    assert len(rows) == 1
    assert rows[0].coefficient_type == "-73"
    assert rows[0].issue_type is SkillComponentSourceAlignmentIssueType.SPECIAL_COEFFICIENT_DISPLAY_MISMATCH


def test_visible_own_dollar_placeholder_is_not_marked_unsupported(tmp_path):
    path = _db(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO skill_rank VALUES (1, 10)")
        db.execute("INSERT INTO skill_coefficient VALUES (1, 3, '-73', 1, 2, 3, 1, 0)")
        db.execute(
            "INSERT INTO ability VALUES (10, '-73', 1, 2, 3, 1, 0, 'Current value $3.', 'Current value <<3>>.')"
        )

    assert SkillComponentSourceAlignmentIssueRepository(path).resolve(1, 3) == ()
