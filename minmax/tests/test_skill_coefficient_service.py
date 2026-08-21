import sqlite3

from services.eso_database import EsoDatabase
from minmax.skill_coefficient_service import (
    SkillCoefficientService,
)


def create_database(path):
    connection = sqlite3.connect(path)

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

    connection.executemany(
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
        [
            (
                4410,
                1,
                "8",
                0.175015,
                1.83764,
                -1.73373,
                1.0,
                5158.7,
            ),
            (
                4410,
                2,
                "8",
                0.0499473,
                0.525132,
                -0.520496,
                1.0,
                1473.25,
            ),
        ],
    )

    connection.commit()
    connection.close()


def test_loads_all_coefficients_for_skill_rank(
    tmp_path,
):
    database_path = tmp_path / "eso.db"

    create_database(database_path)

    database = EsoDatabase(database_path)

    service = SkillCoefficientService(
        database
    )

    coefficients = (
        service.get_for_skill_rank(4410)
    )

    assert len(coefficients) == 2

    assert coefficients[0].coefficient_number == 1
    assert coefficients[0].type == "8"
    assert coefficients[0].a == 0.175015
    assert coefficients[0].b == 1.83764
    assert coefficients[0].c == -1.73373
    assert coefficients[0].r == 1.0

    assert coefficients[1].coefficient_number == 2
    assert coefficients[1].a == 0.0499473
    assert coefficients[1].b == 0.525132
    assert coefficients[1].c == -0.520496

    database.close()


def test_unknown_skill_rank_returns_empty_tuple(
    tmp_path,
):
    database_path = tmp_path / "eso.db"

    create_database(database_path)

    database = EsoDatabase(database_path)

    service = SkillCoefficientService(
        database
    )

    assert (
        service.get_for_skill_rank(999999)
        == ()
    )

    database.close()