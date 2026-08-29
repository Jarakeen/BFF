from __future__ import annotations

import sqlite3

import pytest

from minmax.base_character_state import BaseCharacterCalculator
from minmax.build_calculation_context import BuildCalculationContext
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.core_stat_calculator import CoreStatCalculator, CoreStatInputs
from minmax.derived_stats import DerivedStatInputs, StatContribution
from minmax.skill_coefficient_repository import SkillCoefficientRepository
from minmax.skill_coefficients import (
    SkillCoefficient,
    UnsupportedSkillCoefficientType,
    evaluate_skill_coefficient,
    is_inactive_skill_coefficient,
)
from minmax.skill_tooltip_calculator import SkillTooltipCalculator
from minmax.skill_tooltip_rounding import (
    matching_rounding_policies,
    tooltip_rounding_candidates,
)


def _coefficient_db(tmp_path):
    path = tmp_path / "eso.db"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE skill (
            id INTEGER PRIMARY KEY,
            base_ability_id INTEGER NOT NULL,
            name TEXT
        );
        CREATE TABLE ability (
            ability_id INTEGER PRIMARY KEY,
            name TEXT
        );
        CREATE TABLE skill_rank (
            id INTEGER PRIMARY KEY,
            skill_id INTEGER NOT NULL,
            ability_id INTEGER NOT NULL,
            rank INTEGER,
            morph INTEGER,
            raw_name TEXT
        );
        CREATE TABLE skill_coefficient (
            id INTEGER PRIMARY KEY,
            skill_rank_id INTEGER NOT NULL,
            coefficient_number INTEGER NOT NULL,
            type TEXT,
            a REAL,
            b REAL,
            c REAL,
            r REAL,
            avg REAL
        );

        INSERT INTO skill VALUES (1, 1000, 'Test Skill');
        INSERT INTO ability VALUES (1001, 'Test Morph');
        INSERT INTO ability VALUES (1004, 'Test Morph');
        INSERT INTO skill_rank VALUES (11, 1, 1001, 1, 1, 'Test Morph');
        INSERT INTO skill_rank VALUES (14, 1, 1004, 4, 1, 'Test Morph');

        INSERT INTO skill_coefficient VALUES
            (1, 14, 2, '8', 0.0499473, 0.525132, -0.520496, 1.0, NULL),
            (2, 14, 1, '8', 0.175015, 1.83764, -1.73373, 1.0, NULL),
            (3, 14, 3, '-1', -1.0, -1.0, -1.0, -1.0, NULL);
        """
    )
    connection.commit()
    connection.close()
    return path


def _context() -> BuildCalculationContext:
    attributes = AttributeAllocation(magicka=64)
    progression = CharacterProgression(attributes=attributes)
    state = BaseCharacterCalculator().calculate(attributes=attributes)
    core = CoreStatCalculator().calculate(
        character_progression=progression,
        base_character=state,
        inputs=CoreStatInputs(
            weapon_damage=DerivedStatInputs(
                flat=(StatContribution("test weapon", 2000.0),),
            ),
            spell_damage=DerivedStatInputs(
                flat=(StatContribution("test spell", 4000.0),),
            ),
        ),
    )
    return BuildCalculationContext(
        character_id="character-1",
        build_id="build-1",
        progression=progression,
        character_state=state,
        core_state=core,
    )


def test_type_8_coefficient_preserves_raw_formula_trace():
    coefficient = SkillCoefficient(
        coefficient_number=1,
        type="8",
        a=0.175015,
        b=1.83764,
        c=-1.73373,
        r=1.0,
    )

    result = evaluate_skill_coefficient(coefficient, max_stat=30000, power=5000)

    assert result.resource_term == pytest.approx(5250.45)
    assert result.power_term == pytest.approx(9188.2)
    assert result.before_r == pytest.approx(14436.91627)
    assert result.final_value == pytest.approx(14436.91627)


def test_r_is_applied_after_base_coefficient_expression():
    coefficient = SkillCoefficient(1, "8", 0.1, 1.0, 5.0, r=0.5)

    result = evaluate_skill_coefficient(coefficient, max_stat=20000, power=3000)

    assert result.before_r == pytest.approx(5005.0)
    assert result.final_value == pytest.approx(2502.5)


def test_unsupported_coefficient_type_is_explicit():
    coefficient = SkillCoefficient(1, "12", 0.1, 1.0, 0.0)

    with pytest.raises(UnsupportedSkillCoefficientType):
        evaluate_skill_coefficient(coefficient, max_stat=20000, power=3000)


def test_negative_a_is_not_silently_classified_as_inactive():
    coefficient = SkillCoefficient(
        1,
        "8",
        -0.0000693,
        0.315553,
        -0.593874,
        r=0.999998,
    )

    assert is_inactive_skill_coefficient(coefficient) is False
    result = evaluate_skill_coefficient(
        coefficient,
        max_stat=30000,
        power=5000,
    )
    assert result.final_value > 0


def test_only_exact_uesp_empty_slot_marker_is_inactive():
    sentinel = SkillCoefficient(3, "-1", -1.0, -1.0, -1.0, r=-1.0)
    passive_data = SkillCoefficient(3, "-1", 0.02, 0.0, 0.0, r=-1.0)

    assert is_inactive_skill_coefficient(sentinel) is True
    assert is_inactive_skill_coefficient(passive_data) is False


def test_repository_resolves_highest_rank_and_orders_components(tmp_path):
    path = _coefficient_db(tmp_path)
    repository = SkillCoefficientRepository(path)

    resolution = repository.resolve_name("Test Morph")

    assert resolution.unresolved == ()
    assert resolution.rank is not None
    assert resolution.rank.skill_rank_id == 14
    assert resolution.rank.ability_id == 1004
    assert resolution.rank.rank == 4
    assert [c.coefficient_number for c in resolution.rank.coefficients] == [1, 2, 3]


def test_repository_reports_ambiguous_duplicate_skill_names(tmp_path):
    path = _coefficient_db(tmp_path)
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO skill VALUES (2, 2000, 'Other Skill')")
        connection.execute("INSERT INTO ability VALUES (2004, 'Test Morph')")
        connection.execute("INSERT INTO skill_rank VALUES (24, 2, 2004, 4, 1, 'Test Morph')")
        connection.commit()

    resolution = SkillCoefficientRepository(path).resolve_name("Test Morph")

    assert resolution.rank is None
    assert resolution.unresolved
    assert "Ambiguous skill name" in resolution.unresolved[0]


def test_missing_coefficients_are_not_treated_as_zero_damage(tmp_path):
    path = _coefficient_db(tmp_path)
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO skill VALUES (3, 3000, 'No Coef Skill')")
        connection.execute("INSERT INTO ability VALUES (3004, 'No Coef Morph')")
        connection.execute("INSERT INTO skill_rank VALUES (34, 3, 3004, 4, 1, 'No Coef Morph')")
        connection.commit()

    resolution = SkillCoefficientRepository(path).resolve_name("No Coef Morph")

    assert resolution.rank is not None
    assert resolution.rank.coefficients == ()
    assert resolution.unresolved
    assert "No coefficient rows found" in resolution.unresolved[0]


def test_tooltip_calculator_uses_phase2_context_scaling(tmp_path):
    path = _coefficient_db(tmp_path)
    calculator = SkillTooltipCalculator(SkillCoefficientRepository(path))
    context = _context()

    result = calculator.evaluate_name("Test Morph", context)

    assert result.skill is not None
    assert result.skill.ability_id == 1004
    assert result.scaling is not None
    assert result.scaling.max_magicka == 19104
    assert result.scaling.max_stamina == 12000
    assert result.scaling.highest_max_resource == 19104
    assert result.scaling.weapon_damage == 3000
    assert result.scaling.spell_damage == 5000
    assert result.scaling.highest_offensive_power == 5000
    assert len(result.components) == 2
    assert len(result.inactive_components) == 1
    assert result.inactive_components[0].coefficient_number == 3
    assert result.unresolved == ()

    expected = (
        (0.175015 * 19104) + (1.83764 * 5000) - 1.73373
        + (0.0499473 * 19104) + (0.525132 * 5000) - 0.520496
    )
    assert result.raw_total == pytest.approx(expected)
    assert result.rounding_candidates is not None


def test_tooltip_calculator_evaluates_canonical_entity_id(tmp_path):
    path = _coefficient_db(tmp_path)
    calculator = SkillTooltipCalculator(SkillCoefficientRepository(path))

    result = calculator.evaluate_entity_id("test_morph", _context())

    assert result.unresolved == ()
    assert result.skill is not None
    assert result.skill.entity_id == "test_morph"
    assert result.skill.ability_id == 1004
    assert result.raw_total is not None


def test_tooltip_calculator_reports_unsupported_component_without_guessing(tmp_path):
    path = _coefficient_db(tmp_path)
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE skill_coefficient SET type = '12' WHERE coefficient_number = 2")
        connection.commit()

    result = SkillTooltipCalculator(SkillCoefficientRepository(path)).evaluate_name(
        "Test Morph",
        _context(),
    )

    assert len(result.components) == 1
    assert len(result.inactive_components) == 1
    assert result.raw_total == pytest.approx(result.components[0].final_value)
    assert any("Unsupported skill coefficient type" in message for message in result.unresolved)


def test_tooltip_rounding_candidates_do_not_choose_unverified_policy():
    candidates = tooltip_rounding_candidates(6619.350805)

    assert candidates.floor_value == 6619
    assert candidates.nearest_half_up_value == 6619
    assert candidates.ceiling_value == 6620
    assert candidates.distinct_values == (6619, 6620)
    assert matching_rounding_policies(candidates, 6619) == (
        "floor",
        "nearest-half-up",
    )
    assert matching_rounding_policies(candidates, 6620) == ("ceiling",)
    assert matching_rounding_policies(candidates, 7000) == ()
