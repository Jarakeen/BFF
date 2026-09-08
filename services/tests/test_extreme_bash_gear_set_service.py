import sqlite3

import pytest

from minmax.character_build.weapon_type import WeaponType
from minmax.gear_set_repository import GearSetRepository
from services.extreme_bash_gear_set_service import ExtremeBashGearSetService
from services.extreme_bash_objective_service import (
    ExtremeBashBarWeapons,
    ExtremeBashDamageInputs,
    ExtremeBashLegalityContext,
)


def _database(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE gear_set (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                max_equip_count INTEGER
            );
            CREATE TABLE gear_set_bonus (
                id INTEGER PRIMARY KEY,
                set_id INTEGER NOT NULL,
                piece_count INTEGER NOT NULL,
                description TEXT
            );
            """
        )
        connection.executemany(
            "INSERT INTO gear_set VALUES (?, ?, ?, ?)",
            [
                (1, "Bash Wall", "Crafted", 5),
                (2, "Armor Wall", "Crafted", 5),
                (3, "Mystery Bash", "Crafted", 5),
            ],
        )
        connection.executemany(
            "INSERT INTO gear_set_bonus VALUES (?, ?, ?, ?)",
            [
                (1, 1, 2, "(2 items) Adds 34-1487 Armor"),
                (2, 1, 5, "(5 items) Increases your Bash damage by 935."),
                (3, 2, 5, "(5 items) Adds 46-2000 Armor"),
                (
                    4,
                    3,
                    5,
                    "(5 items) When you Bash an enemy, gain a mysterious proc for 5 seconds.",
                ),
            ],
        )
    return path


def _legal():
    return ExtremeBashLegalityContext(
        front=ExtremeBashBarWeapons(WeaponType.SWORD, WeaponType.SHIELD),
        back=ExtremeBashBarWeapons(WeaponType.MACE, WeaponType.SHIELD),
    )


def _complete_inputs():
    return ExtremeBashDamageInputs(
        spell_resist=1000.0,
        physical_resist=1000.0,
        cp_bash_damage=120.0,
        skill2_bash_damage=0.0,
        physical_damage_done=0.0,
        damage_done=0.0,
        direct_damage_done=0.0,
        single_target_damage_done=0.0,
        skill_bash_damage=0.0,
        set_extra_bash_damage=0.0,
        skill_extra_bash_damage=0.0,
        item_extra_bash_damage=300.0,
    )


def test_candidate_keeps_flat_bash_and_resistance_channels_together(tmp_path):
    repository = GearSetRepository(_database(tmp_path))

    candidate = ExtremeBashGearSetService.candidate_for_set(repository, "Bash Wall")

    assert candidate.extra_bash_damage == pytest.approx(935.0)
    assert candidate.physical_resistance == pytest.approx(1487.0)
    assert candidate.spell_resistance == pytest.approx(1487.0)
    assert candidate.max_resistance_delta == pytest.approx(1487.0)
    assert candidate.unresolved == ()
    assert candidate.mechanic_complete is True


def test_candidate_evaluation_applies_resistance_before_canonical_bash_formula(tmp_path):
    repository = GearSetRepository(_database(tmp_path))
    candidate = ExtremeBashGearSetService.candidate_for_set(repository, "Bash Wall")

    result = ExtremeBashGearSetService.evaluate_candidate(
        candidate,
        _complete_inputs(),
        legality=_legal(),
    )

    expected = (
        (2487.0 * 0.011250 + 1.0 + 120.0)
        + 935.0
        + 300.0
    )
    assert result.objective.reviewed_value == pytest.approx(expected)
    assert result.objective.mechanic_complete is True


def test_resistance_only_set_can_beat_no_set_because_bash_scales_from_resistance(tmp_path):
    repository = GearSetRepository(_database(tmp_path))
    candidate = ExtremeBashGearSetService.candidate_for_set(repository, "Armor Wall")

    result = ExtremeBashGearSetService.evaluate_candidate(
        candidate,
        _complete_inputs(),
        legality=_legal(),
    )

    baseline = 1000.0 * 0.011250 + 1.0 + 120.0 + 300.0
    assert result.objective.reviewed_value > baseline
    assert result.candidate.extra_bash_damage == 0.0
    assert result.candidate.max_resistance_delta == 2000.0


def test_unmapped_active_bash_proc_remains_a_blocker(tmp_path):
    repository = GearSetRepository(_database(tmp_path))
    candidate = ExtremeBashGearSetService.candidate_for_set(repository, "Mystery Bash")

    result = ExtremeBashGearSetService.evaluate_candidate(
        candidate,
        _complete_inputs(),
        legality=_legal(),
    )

    assert candidate.mechanic_complete is False
    assert any("mysterious proc" in problem for problem in candidate.unresolved)
    assert any(
        channel.startswith("gear_set:")
        for channel in result.objective.unresolved_channels
    )
    assert result.objective.mechanic_complete is False


def test_ranker_uses_coupled_final_bash_value_not_raw_bash_text_only(tmp_path):
    repository = GearSetRepository(_database(tmp_path))

    rows = ExtremeBashGearSetService.candidates_for_objective(
        repository,
        _complete_inputs(),
        legality=_legal(),
    )

    complete = [row for row in rows if row.objective.mechanic_complete]
    assert {row.candidate.set_name for row in complete} == {"Armor Wall", "Bash Wall"}
    assert complete[0].objective.reviewed_value >= complete[1].objective.reviewed_value
    assert rows[-1].candidate.set_name == "Mystery Bash"
