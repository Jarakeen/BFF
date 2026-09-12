import sqlite3

import minmax.skill_component_damage_scaling_repository as damage_scaling_module
from minmax.skill_component_damage_scaling import SkillComponentDamageScalingType
from minmax.skill_component_damage_scaling_repository import SkillComponentDamageScalingRepository


def _make_db(path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, ability_id INTEGER NOT NULL);
        CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT);
        INSERT INTO skill_rank VALUES (10, 100);
        INSERT INTO ability VALUES (
            100,
            'Deal $1 Magic Damage. After the duration ends, deal $2 Magic Damage, which increases based on the amount of damage you dealt over the duration, up to 200%.'
        );
        INSERT INTO skill_rank VALUES (20, 200);
        INSERT INTO ability VALUES (
            200,
            'Enemies take $1 Magic Damage every 2 seconds for 20 seconds which increases by 12% per tick.'
        );
        INSERT INTO skill_rank VALUES (30, 300);
        INSERT INTO ability VALUES (
            300,
            'Craft a rune that deals $1 Magic Damage and heals you for $2 Health, scaling off your Max Health.'
        );
        """
    )
    db.commit()
    db.close()


def test_repository_resolves_accumulated_and_per_tick_scaling(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)
    repo = SkillComponentDamageScalingRepository(path)

    stored = repo.resolve(10, 2)
    ramp = repo.resolve(20, 1)

    assert [row.scaling_type for row in stored] == [SkillComponentDamageScalingType.ACCUMULATED_DAMAGE]
    assert stored[0].max_bonus_fraction == 2.0
    assert [row.scaling_type for row in ramp] == [SkillComponentDamageScalingType.PER_TICK_INCREMENT]
    assert ramp[0].increment_fraction == 0.12


def test_repository_does_not_borrow_neighbor_heal_scaling(tmp_path):
    path = tmp_path / "eso.db"
    _make_db(path)
    repo = SkillComponentDamageScalingRepository(path)
    assert repo.resolve(30, 1) == ()


def test_repository_fails_closed_when_tables_are_missing(tmp_path):
    path = tmp_path / "eso.db"
    sqlite3.connect(path).close()
    assert SkillComponentDamageScalingRepository(path).resolve(10, 1) == ()


def test_repository_reuses_rank_source_across_component_lookups(tmp_path, monkeypatch):
    path = tmp_path / "eso.db"
    _make_db(path)

    original_connect = damage_scaling_module.sqlite3.connect
    connect_count = 0

    def counting_connect(*args, **kwargs):
        nonlocal connect_count
        connect_count += 1
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(damage_scaling_module.sqlite3, "connect", counting_connect)
    repository = SkillComponentDamageScalingRepository(path)

    stored = repository.resolve(10, 2)
    base = repository.resolve(10, 1)
    stored_again = repository.resolve(10, 2)

    assert [row.scaling_type for row in stored] == [
        SkillComponentDamageScalingType.ACCUMULATED_DAMAGE
    ]
    assert base == ()
    assert stored_again == stored
    assert connect_count == 1

    fresh_repository = SkillComponentDamageScalingRepository(path)
    assert fresh_repository.resolve(10, 2) == stored
    assert connect_count == 2
