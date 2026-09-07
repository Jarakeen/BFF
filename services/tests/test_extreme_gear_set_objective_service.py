from __future__ import annotations

import pytest

from minmax.gear_sets import GearSet, GearSetBonus
from minmax.gear_stat_inputs import GearStatInputResolver
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


class _Repo:
    def __init__(self, sets, bonuses):
        self._sets = tuple(sets)
        self._bonuses = {int(key): tuple(value) for key, value in bonuses.items()}

    def list_sets(self):
        return self._sets

    def get_set(self, name):
        return next((row for row in self._sets if row.name == name), None)

    def get_bonuses(self, set_id):
        return list(self._bonuses.get(int(set_id), ()))


def _bonus(bonus_id, set_id, pieces, description):
    return GearSetBonus(
        id=bonus_id,
        set_id=set_id,
        piece_count=pieces,
        description=description,
    )


def test_static_set_bonus_projects_weapon_and_spell_damage():
    gear_set = GearSet(1, "Static Power", "Test", 5)
    repo = _Repo(
        [gear_set],
        {
            1: [
                _bonus(1, 1, 2, "Adds 129 Weapon and Spell Damage"),
                _bonus(2, 1, 5, "Adds 171 Weapon and Spell Damage"),
            ]
        },
    )

    row = ExtremeGearSetObjectiveService.candidate_for_set(repo, "Static Power", "spell_damage")

    assert row.reviewed_delta == 300.0
    assert row.mechanic_complete is True
    assert row.unresolved == ()


def test_unmapped_active_bonus_preserves_known_lower_bound_and_blocker():
    gear_set = GearSet(2, "Mystery Five Piece", "Test", 5)
    repo = _Repo(
        [gear_set],
        {
            2: [
                _bonus(1, 2, 2, "Adds 129 Weapon and Spell Damage"),
                _bonus(
                    2,
                    2,
                    5,
                    "When you do something dramatic, gain an effect whose mechanic is not mapped yet.",
                ),
            ]
        },
    )

    row = ExtremeGearSetObjectiveService.candidate_for_set(
        repo,
        "Mystery Five Piece",
        "spell_damage",
    )

    assert row.reviewed_delta == 129.0
    assert row.mechanic_complete is False
    assert row.unresolved
    assert "not yet mechanic-mapped" in row.unresolved[0]
    assert "gain an effect" in row.unresolved[0].casefold()


def test_unresolved_bonus_is_never_treated_as_zero_complete_mechanic():
    gear_set = GearSet(3, "Only Mystery", "Test", 1)
    repo = _Repo(
        [gear_set],
        {3: [_bonus(1, 3, 1, "While a condition is true, become mysteriously stronger.")]},
    )

    row = ExtremeGearSetObjectiveService.candidate_for_set(
        repo,
        "Only Mystery",
        "physical_resistance",
    )

    assert row.reviewed_delta == 0.0
    assert row.mechanic_complete is False
    assert row.unresolved


def test_conditional_critical_damage_keeps_base_lower_bound_and_condition_blocker():
    gear_set = GearSet(4, "Archer Pattern", "Test", 5)
    repo = _Repo(
        [gear_set],
        {
            4: [
                _bonus(
                    1,
                    4,
                    5,
                    "Increases your Critical Damage and Healing by 5%. "
                    "Increases your Critical Damage and Healing by an additional 10% "
                    "when you are Sneaking or Invisible.",
                )
            ]
        },
    )

    row = ExtremeGearSetObjectiveService.candidate_for_set(
        repo,
        "Archer Pattern",
        "critical_damage",
    )

    assert row.reviewed_delta == pytest.approx(0.05)
    assert row.mechanic_complete is False
    assert any("sneaking_or_invisible" in item for item in row.unresolved)


def test_critical_chance_set_bonus_uses_authoritative_rating_conversion():
    gear_set = GearSet(5, "Crit Set", "Test", 2)
    repo = _Repo(
        [gear_set],
        {5: [_bonus(1, 5, 2, "Adds 657 Critical Chance")]},
    )

    row = ExtremeGearSetObjectiveService.candidate_for_set(repo, "Crit Set", "spell_critical")

    assert row.reviewed_delta == pytest.approx(
        GearStatInputResolver.critical_rating_to_ratio(657.0)
    )
    assert row.mechanic_complete is True


def test_piece_count_only_activates_reached_bonuses():
    gear_set = GearSet(6, "Piece Gate", "Test", 5)
    repo = _Repo(
        [gear_set],
        {
            6: [
                _bonus(1, 6, 2, "Adds 129 Weapon and Spell Damage"),
                _bonus(2, 6, 5, "Adds 171 Weapon and Spell Damage"),
            ]
        },
    )

    row = ExtremeGearSetObjectiveService.candidate_for_set(
        repo,
        "Piece Gate",
        "weapon_damage",
        equipped_piece_count=2,
    )

    assert row.reviewed_delta == 129.0
    assert len(row.source_bonuses) == 1


def test_piece_count_above_canonical_max_is_rejected():
    gear_set = GearSet(7, "Five Piece", "Test", 5)
    repo = _Repo([gear_set], {7: []})

    with pytest.raises(ValueError, match="exceeds canonical max"):
        ExtremeGearSetObjectiveService.candidate_for_set(
            repo,
            "Five Piece",
            "spell_damage",
            equipped_piece_count=6,
        )


def test_candidates_sort_mechanic_complete_sets_before_incomplete_sets():
    complete = GearSet(8, "Complete", "Test", 2)
    incomplete = GearSet(9, "Incomplete", "Test", 2)
    repo = _Repo(
        [incomplete, complete],
        {
            8: [_bonus(1, 8, 2, "Adds 100 Weapon and Spell Damage")],
            9: [_bonus(2, 9, 2, "An unresolved bonus worth an unknown amount.")],
        },
    )

    rows = ExtremeGearSetObjectiveService.candidates_for_objective(repo, "spell_damage")

    assert [row.set_name for row in rows] == ["Complete", "Incomplete"]
    assert rows[0].mechanic_complete is True
    assert rows[1].mechanic_complete is False


def test_unknown_objective_is_rejected():
    repo = _Repo([], {})

    with pytest.raises(KeyError, match="unreviewed Extreme gear-set objective"):
        ExtremeGearSetObjectiveService.candidates_for_objective(repo, "max_health")
