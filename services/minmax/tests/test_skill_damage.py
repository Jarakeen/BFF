import sqlite3

import pytest

from services.eso_database import EsoDatabase
from services.minmax.skill_coefficient_service import (
    SkillCoefficientService,
)
from services.minmax.skill_damage import (
    SkillDamageService,
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
            (
                4410,
                3,
                "-1",
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
            ),
        ],
    )

    connection.commit()
    connection.close()


def test_skill_damage_evaluates_all_active_components(
    tmp_path,
):
    database_path = tmp_path / "eso.db"

    create_database(database_path)

    database = EsoDatabase(database_path)

    service = SkillDamageService(
        SkillCoefficientService(database)
    )

    result = service.evaluate(
        4410,
        max_stat=30000,
        power=6000,
    )

    expected_first = (
        0.175015 * 30000
        + 1.83764 * 6000
        - 1.73373
    )

    expected_second = (
        0.0499473 * 30000
        + 0.525132 * 6000
        - 0.520496
    )

    assert len(result.components) == 2

    assert result.components[0].raw_value == pytest.approx(
        expected_first
    )

    assert result.components[1].raw_value == pytest.approx(
        expected_second
    )

    assert result.total_raw_damage == pytest.approx(
        expected_first + expected_second
    )

    database.close()


def test_empty_skill_has_zero_damage(
    tmp_path,
):
    database_path = tmp_path / "eso.db"

    create_database(database_path)

    database = EsoDatabase(database_path)

    service = SkillDamageService(
        SkillCoefficientService(database)
    )

    result = service.evaluate(
        999999,
        max_stat=30000,
        power=6000,
    )

    assert result.components == ()
    assert result.total_raw_damage == 0

    database.close()
    