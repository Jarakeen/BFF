from __future__ import annotations

import pytest

from minmax.gear_stat_inputs import GearStatInputResolver
from minmax.mundus_repository import (
    MundusEffectRecord,
    MundusRepository,
    U50_GAME_UPDATE,
    U51_GAME_UPDATE,
)
from minmax.stat_ids import StatId
from services.extreme_mundus_objective_service import ExtremeMundusObjectiveService


@pytest.fixture
def u50_repository(tmp_path):
    return MundusRepository(tmp_path / "u50.db", game_update=U50_GAME_UPDATE)


@pytest.fixture
def u51_repository(tmp_path):
    return MundusRepository(tmp_path / "u51.db", game_update=U51_GAME_UPDATE)


@pytest.mark.parametrize(
    ("objective", "expected_name", "expected_delta"),
    [
        ("critical_damage", "The Shadow", 0.11),
        ("magicka_recovery", "The Atronach", 310.0),
        ("stamina_recovery", "The Serpent", 310.0),
        ("physical_resistance", "The Lady", 2744.0),
        ("spell_resistance", "The Lady", 2744.0),
        ("spell_damage", "The Apprentice", 238.0),
        ("weapon_damage", "The Warrior", 238.0),
    ],
)
def test_update_50_best_mundus_projects_in_extreme_objective_units(
    u50_repository,
    objective,
    expected_name,
    expected_delta,
):
    best = ExtremeMundusObjectiveService.best_for_objective(u50_repository, objective)

    assert best is not None
    assert best.mundus_name == expected_name
    assert best.projected_delta == pytest.approx(expected_delta)
    assert best.unresolved == ()


@pytest.mark.parametrize("objective", ["spell_critical", "weapon_critical"])
def test_thief_uses_authoritative_critical_rating_conversion(u50_repository, objective):
    best = ExtremeMundusObjectiveService.best_for_objective(u50_repository, objective)

    assert best is not None
    assert best.mundus_name == "The Thief"
    assert best.projected_delta == pytest.approx(
        GearStatInputResolver.critical_rating_to_ratio(1333.0)
    )


def test_mundus_multiplier_is_applied_before_objective_unit_conversion(u50_repository):
    shadow = ExtremeMundusObjectiveService.candidate_for_name(
        u50_repository,
        "The Shadow",
        "critical_damage",
        multiplier=1.5,
    )
    thief = ExtremeMundusObjectiveService.candidate_for_name(
        u50_repository,
        "The Thief",
        "spell_critical",
        multiplier=1.5,
    )

    assert shadow.projected_delta == pytest.approx(0.165)
    assert thief.projected_delta == pytest.approx(
        GearStatInputResolver.critical_rating_to_ratio(1333.0 * 1.5)
    )


def test_update_51_repository_changes_are_inherited_instead_of_hardcoded(u51_repository):
    spell = ExtremeMundusObjectiveService.best_for_objective(
        u51_repository,
        "spell_damage",
    )
    weapon = ExtremeMundusObjectiveService.best_for_objective(
        u51_repository,
        "weapon_damage",
    )
    apprentice = ExtremeMundusObjectiveService.candidate_for_name(
        u51_repository,
        "The Apprentice",
        "spell_damage",
    )

    assert spell is not None and spell.mundus_name == "The Warrior"
    assert spell.projected_delta == pytest.approx(238.0)
    assert weapon is not None and weapon.mundus_name == "The Warrior"
    assert weapon.projected_delta == pytest.approx(238.0)
    assert apprentice.projected_delta == pytest.approx(0.0)


class _UnsupportedRelevantRepository:
    def list_names(self):
        return ["Mystery Stone"]

    def get_records(self, name):
        return [
            MundusEffectRecord(
                name=name,
                stat_id=StatId.SPELL_DAMAGE.value,
                value=999.0,
                unit="flat",
                supported=False,
                notes="fixture deliberately unresolved",
            )
        ]


def test_relevant_unsupported_mundus_record_fails_closed_instead_of_scoring_zero():
    row = ExtremeMundusObjectiveService.candidate_for_name(
        _UnsupportedRelevantRepository(),
        "Mystery Stone",
        "spell_damage",
    )

    assert row.projected_delta is None
    assert len(row.unresolved) == 1
    assert "fixture deliberately unresolved" in row.unresolved[0]


def test_unreviewed_objective_and_negative_multiplier_are_rejected(u50_repository):
    with pytest.raises(KeyError, match="unreviewed Extreme Mundus objective"):
        ExtremeMundusObjectiveService.best_for_objective(u50_repository, "max_health")

    with pytest.raises(ValueError, match="non-negative"):
        ExtremeMundusObjectiveService.best_for_objective(
            u50_repository,
            "spell_damage",
            multiplier=-1.0,
        )
