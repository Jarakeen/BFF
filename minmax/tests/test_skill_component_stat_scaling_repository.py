import sqlite3

from minmax.skill_component_stat_scaling import (
    SkillComponentScaledStat,
    SkillComponentStatScalingDriver,
)
from minmax.skill_component_stat_scaling_repository import SkillComponentStatScalingRepository


def test_repository_resolves_color_tagged_elder_dragon_source(tmp_path):
    db_path = tmp_path / "eso.db"
    with sqlite3.connect(db_path) as db:
        db.executescript(
            """
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                coef_description TEXT
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                ability_id INTEGER
            );
            INSERT INTO ability VALUES (
                29460,
                'Increases your Health Recovery by up to |cffffff350|r, based on your missing Health. Current amount: |cffffff$1|r'
            );
            INSERT INTO skill_rank VALUES (5578, 29460);
            """
        )

    rows = SkillComponentStatScalingRepository(db_path).resolve(5578, 1)
    assert len(rows) == 1
    assert rows[0].stat is SkillComponentScaledStat.HEALTH_RECOVERY
    assert rows[0].scaling_driver is SkillComponentStatScalingDriver.MISSING_HEALTH
    assert rows[0].maximum_bonus == 350.0
