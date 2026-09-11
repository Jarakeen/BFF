from __future__ import annotations

import pytest

from minmax.champion_point_static_repository import (
    CHAMPION_SKILL_TYPE_NORMAL,
    CHAMPION_SKILL_TYPE_NORMAL_SLOTTABLE,
    ChampionPointRecord,
)
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.gear_stat_inputs import GearStatInputResolver
from minmax.stat_ids import StatId
from services.extreme_champion_point_objective_service import (
    ExtremeChampionPointObjectiveService,
)


def _record(name: str, *, slottable: bool = False, max_points: int = 50) -> ChampionPointRecord:
    return ChampionPointRecord(
        name=name,
        skill_type=(
            CHAMPION_SKILL_TYPE_NORMAL_SLOTTABLE
            if slottable
            else CHAMPION_SKILL_TYPE_NORMAL
        ),
        max_points=max_points,
        jump_points=(),
        description="fixture",
    )


class _Repository:
    def __init__(self, *, non_slottable=(), slottable=(), resolved=None):
        self._non_slottable = tuple(non_slottable)
        self._slottable = tuple(slottable)
        self._resolved = dict(resolved or {})

    def non_slottable_records(self):
        return self._non_slottable

    def slottable_records(self):
        return self._slottable

    def resolve(self, name, points):
        return self._resolved[name]


def test_flat_static_cp_projects_directly_into_extreme_objective():
    record = _record("Fortified")
    repo = _Repository(
        non_slottable=(record,),
        resolved={
            "Fortified": (
                [
                    Effect(
                        source="Champion Point: Fortified",
                        stat=StatId.PHYSICAL_RESISTANCE,
                        operation=EffectOperation.ADD,
                        value=1731.0,
                        unit=EffectUnit.FLAT,
                    )
                ],
                [],
            )
        },
    )

    row = ExtremeChampionPointObjectiveService.candidate_for_record(
        repo,
        record,
        "physical_resistance",
    )

    assert row.reviewed_delta == pytest.approx(1731.0)
    assert row.unresolved == ()


@pytest.mark.parametrize(
    ("objective_key", "stat", "amount"),
    (
        ("max_health", StatId.MAX_HEALTH, 1400.0),
        ("max_magicka", StatId.MAX_MAGICKA, 1300.0),
        ("max_stamina", StatId.MAX_STAMINA, 1250.0),
    ),
)
def test_max_resource_static_cp_projects_directly(objective_key, stat, amount):
    record = _record("Resource Star")
    repo = _Repository(
        non_slottable=(record,),
        resolved={
            "Resource Star": (
                [
                    Effect(
                        source="Champion Point: Resource Star",
                        stat=stat,
                        operation=EffectOperation.ADD,
                        value=amount,
                        unit=EffectUnit.FLAT,
                    )
                ],
                [],
            )
        },
    )

    row = ExtremeChampionPointObjectiveService.candidate_for_record(
        repo,
        record,
        objective_key,
    )

    assert row.reviewed_delta == pytest.approx(amount)
    assert row.unresolved == ()


def test_resource_objective_ignores_other_resource_effects_without_guessing():
    record = _record("Mixed Resources")
    repo = _Repository(
        non_slottable=(record,),
        resolved={
            "Mixed Resources": (
                [
                    Effect(
                        source="Champion Point: Mixed Resources",
                        stat=StatId.MAX_HEALTH,
                        operation=EffectOperation.ADD,
                        value=1400.0,
                        unit=EffectUnit.FLAT,
                    ),
                    Effect(
                        source="Champion Point: Mixed Resources",
                        stat=StatId.MAX_MAGICKA,
                        operation=EffectOperation.ADD,
                        value=1300.0,
                        unit=EffectUnit.FLAT,
                    ),
                ],
                [],
            )
        },
    )

    row = ExtremeChampionPointObjectiveService.candidate_for_record(
        repo,
        record,
        "max_magicka",
    )

    assert row.reviewed_delta == pytest.approx(1300.0)
    assert row.unresolved == ()


def test_critical_damage_percent_is_converted_to_ratio():
    record = _record("Fighting Finesse", slottable=True)
    repo = _Repository(
        slottable=(record,),
        resolved={
            "Fighting Finesse": (
                [
                    Effect(
                        source="Champion Point: Fighting Finesse",
                        stat=StatId.CRITICAL_DAMAGE,
                        operation=EffectOperation.ADD_PERCENT,
                        value=8.0,
                        unit=EffectUnit.PERCENT,
                    )
                ],
                [],
            )
        },
    )

    row = ExtremeChampionPointObjectiveService.candidate_for_record(
        repo,
        record,
        "critical_damage",
    )

    assert row.reviewed_delta == pytest.approx(0.08)


def test_critical_chance_rating_uses_existing_authoritative_conversion():
    record = _record("Precision")
    repo = _Repository(
        non_slottable=(record,),
        resolved={
            "Precision": (
                [
                    Effect(
                        source="Champion Point: Precision",
                        stat=StatId.CRITICAL_CHANCE,
                        operation=EffectOperation.ADD,
                        value=1400.0,
                        unit=EffectUnit.FLAT,
                    )
                ],
                [],
            )
        },
    )

    row = ExtremeChampionPointObjectiveService.candidate_for_record(
        repo,
        record,
        "spell_critical",
    )

    assert row.reviewed_delta == pytest.approx(
        GearStatInputResolver.critical_rating_to_ratio(1400.0)
    )


def test_percent_reference_effect_refuses_fake_fixed_value_without_reference():
    record = _record("Percent Power")
    repo = _Repository(
        non_slottable=(record,),
        resolved={
            "Percent Power": (
                [
                    Effect(
                        source="Champion Point: Percent Power",
                        stat=StatId.SPELL_DAMAGE,
                        operation=EffectOperation.ADD_PERCENT,
                        value=5.0,
                        unit=EffectUnit.PERCENT,
                    )
                ],
                [],
            )
        },
    )

    unresolved = ExtremeChampionPointObjectiveService.candidate_for_record(
        repo,
        record,
        "spell_damage",
    )
    resolved = ExtremeChampionPointObjectiveService.candidate_for_record(
        repo,
        record,
        "spell_damage",
        reference_value=4000.0,
    )

    assert unresolved.reviewed_delta is None
    assert "requires a reference value" in unresolved.unresolved[0]
    assert resolved.reviewed_delta == pytest.approx(200.0)


def test_unmapped_cp_is_a_blocker_not_a_zero_value_candidate():
    record = _record("Mystery Star")
    repo = _Repository(
        non_slottable=(record,),
        resolved={
            "Mystery Star": (
                [],
                ["Champion Point is dynamic or not yet stat-mapped: Mystery Star"],
            )
        },
    )

    row = ExtremeChampionPointObjectiveService.candidate_for_record(
        repo,
        record,
        "weapon_damage",
    )

    assert row.reviewed_delta is None
    assert row.unresolved


def test_known_external_dynamic_cp_remains_explicit_extreme_blocker():
    record = _record("Swift Renewal", slottable=True)
    repo = _Repository(slottable=(record,), resolved={"Swift Renewal": ([], [])})

    row = ExtremeChampionPointObjectiveService.candidate_for_record(
        repo,
        record,
        "spell_damage",
    )

    assert row.reviewed_delta is None
    assert "runtime/dynamic Extreme context" in row.unresolved[0]


def test_non_slottable_baseline_keeps_numeric_lower_bound_and_unresolved_blockers():
    armor = _record("Fortified")
    mystery = _record("Mystery Star")
    repo = _Repository(
        non_slottable=(armor, mystery),
        resolved={
            "Fortified": (
                [
                    Effect(
                        source="Champion Point: Fortified",
                        stat=StatId.PHYSICAL_RESISTANCE,
                        operation=EffectOperation.ADD,
                        value=1731.0,
                        unit=EffectUnit.FLAT,
                    )
                ],
                [],
            ),
            "Mystery Star": (
                [],
                ["Champion Point is dynamic or not yet stat-mapped: Mystery Star"],
            ),
        },
    )

    baseline = ExtremeChampionPointObjectiveService.non_slottable_baseline_for_objective(
        repo,
        "physical_resistance",
    )

    assert baseline.reviewed_lower_bound == pytest.approx(1731.0)
    assert len(baseline.resolved_candidates) == 1
    assert len(baseline.unresolved_candidates) == 1
    assert baseline.mechanic_complete is False


def test_slottable_inventory_is_ranked_without_claiming_a_legal_four_star_loadout():
    stronger = _record("Strong Star", slottable=True)
    weaker = _record("Weak Star", slottable=True)
    mystery = _record("Mystery Star", slottable=True)
    repo = _Repository(
        slottable=(weaker, mystery, stronger),
        resolved={
            "Strong Star": (
                [
                    Effect(
                        source="Champion Point: Strong Star",
                        stat=StatId.WEAPON_DAMAGE,
                        operation=EffectOperation.ADD,
                        value=300.0,
                        unit=EffectUnit.FLAT,
                    )
                ],
                [],
            ),
            "Weak Star": (
                [
                    Effect(
                        source="Champion Point: Weak Star",
                        stat=StatId.WEAPON_DAMAGE,
                        operation=EffectOperation.ADD,
                        value=100.0,
                        unit=EffectUnit.FLAT,
                    )
                ],
                [],
            ),
            "Mystery Star": (
                [],
                ["Champion Point is dynamic or not yet stat-mapped: Mystery Star"],
            ),
        },
    )

    rows = ExtremeChampionPointObjectiveService.slottable_candidates_for_objective(
        repo,
        "weapon_damage",
    )

    assert [row.name for row in rows] == ["Strong Star", "Weak Star", "Mystery Star"]
    assert rows[-1].reviewed_delta is None


def test_unreviewed_objective_is_rejected():
    with pytest.raises(KeyError, match="unreviewed Extreme Champion Point objective"):
        ExtremeChampionPointObjectiveService.non_slottable_baseline_for_objective(
            _Repository(),
            "max_ultimate",
        )
