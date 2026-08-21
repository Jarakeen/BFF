import json
import sqlite3

from services.minmax.skill_coefficient_reconciler import (
    SkillCoefficientReconciler,
)


def create_database(path):
    connection = sqlite3.connect(path)

    connection.execute(
        """
        CREATE TABLE skill_rank (
            id INTEGER PRIMARY KEY,
            ability_id INTEGER NOT NULL UNIQUE
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE skill_coefficient (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_rank_id INTEGER NOT NULL,
            coefficient_number INTEGER NOT NULL,
            type TEXT,
            a REAL,
            b REAL,
            c REAL,
            r REAL,
            avg REAL
        )
        """
    )

    connection.commit()
    connection.close()


def test_reconciler_maps_ability_id_to_current_rank_id(
    tmp_path,
):
    database_path = (
        tmp_path / "eso.db"
    )

    coefficient_path = (
        tmp_path / "skill_coef_raw.json"
    )

    create_database(
        database_path
    )

    connection = sqlite3.connect(
        database_path
    )

    connection.execute(
        """
        INSERT INTO skill_rank (
            id,
            ability_id
        )
        VALUES (?, ?)
        """,
        (
            5000,
            12345,
        ),
    )

    connection.execute(
        """
        INSERT INTO skill_coefficient (
            skill_rank_id,
            coefficient_number,
            type,
            a,
            b,
            c,
            r,
            avg
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            1,
            "8",
            1.0,
            2.0,
            3.0,
            1.0,
            100.0,
        ),
    )

    connection.commit()
    connection.close()

    coefficient_path.write_text(
        json.dumps(
            {
                "numRecords": 1,
                "skillCoef": [
                    {
                        "id": "12345",
                        "type1": "8",
                        "a1": "1.0",
                        "b1": "2.0",
                        "c1": "3.0",
                        "R1": "1.0",
                        "avg1": "100.0",
                        "type2": "-1",
                        "a2": "-1",
                        "b2": "-1",
                        "c2": "-1",
                        "R2": "-1",
                        "avg2": "-1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = SkillCoefficientReconciler(
        database=database_path,
        coefficient_file=coefficient_path,
    ).run()

    assert result["matched_abilities"] == 1
    assert result["coefficient_rows"] == 2

    connection = sqlite3.connect(
        database_path
    )

    rows = connection.execute(
        """
        SELECT
            skill_rank_id,
            coefficient_number,
            type,
            a,
            b,
            c,
            r,
            avg
        FROM skill_coefficient
        ORDER BY coefficient_number
        """
    ).fetchall()

    orphaned = connection.execute(
        """
        SELECT COUNT(*)
        FROM skill_coefficient sc
        LEFT JOIN skill_rank sr
            ON sr.id = sc.skill_rank_id
        WHERE sr.id IS NULL
        """
    ).fetchone()[0]

    connection.close()

    assert rows[0] == (
        5000,
        1,
        "8",
        1.0,
        2.0,
        3.0,
        1.0,
        100.0,
    )

    assert rows[1] == (
        5000,
        2,
        "-1",
        -1.0,
        -1.0,
        -1.0,
        -1.0,
        -1.0,
    )

    assert orphaned == 0


def test_unmatched_raw_abilities_are_not_inserted(
    tmp_path,
):
    database_path = (
        tmp_path / "eso.db"
    )

    coefficient_path = (
        tmp_path / "skill_coef_raw.json"
    )

    create_database(
        database_path
    )

    connection = sqlite3.connect(
        database_path
    )

    connection.execute(
        """
        INSERT INTO skill_rank (
            id,
            ability_id
        )
        VALUES (?, ?)
        """,
        (
            5000,
            12345,
        ),
    )

    connection.commit()
    connection.close()

    coefficient_path.write_text(
        json.dumps(
            {
                "numRecords": 2,
                "skillCoef": [
                    {
                        "id": "12345",
                        "type1": "8",
                        "a1": "1",
                        "b1": "2",
                        "c1": "3",
                        "R1": "1",
                        "avg1": "100",
                    },
                    {
                        "id": "99999",
                        "type1": "8",
                        "a1": "4",
                        "b1": "5",
                        "c1": "6",
                        "R1": "1",
                        "avg1": "200",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    result = SkillCoefficientReconciler(
        database=database_path,
        coefficient_file=coefficient_path,
    ).run()

    assert result["matched_abilities"] == 1
    assert result["unmatched_raw"] == 1
    assert result["coefficient_rows"] == 1