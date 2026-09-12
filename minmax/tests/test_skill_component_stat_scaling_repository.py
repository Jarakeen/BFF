import sqlite3

import minmax.skill_component_stat_scaling_repository as stat_scaling_module
from minmax.skill_component_stat_scaling import (
    SkillComponentScaledStat,
    SkillComponentStatScalingDriver,
)
from minmax.skill_component_stat_scaling_repository import SkillComponentStatScalingRepository


def _database(tmp_path):
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
    return db_path


def test_repository_resolves_color_tagged_elder_dragon_source(tmp_path):
    rows = SkillComponentStatScalingRepository(_database(tmp_path)).resolve(5578, 1)

    assert len(rows) == 1
    assert rows[0].stat is SkillComponentScaledStat.HEALTH_RECOVERY
    assert rows[0].scaling_driver is SkillComponentStatScalingDriver.MISSING_HEALTH
    assert rows[0].maximum_bonus == 350.0


def test_repository_reuses_source_text_across_component_numbers(monkeypatch, tmp_path):
    db_path = _database(tmp_path)
    original_connect = stat_scaling_module.sqlite3.connect
    connect_count = 0

    def counting_connect(*args, **kwargs):
        nonlocal connect_count
        connect_count += 1
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(stat_scaling_module.sqlite3, "connect", counting_connect)
    repository = SkillComponentStatScalingRepository(db_path)

    first = repository.resolve(5578, 1)
    repository.resolve(5578, 2)
    first_again = repository.resolve(5578, 1)

    assert first_again == first
    assert connect_count == 1

    fresh_repository = SkillComponentStatScalingRepository(db_path)
    assert fresh_repository.resolve(5578, 1) == first
    assert connect_count == 2
