from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_arcanist_fated_fortune_critical_healing_service import (
    ExtremeArcanistFatedFortuneCriticalHealingService,
)


class _SkillLines:
    @staticmethod
    def passive_max_rank(name):
        if str(name) == "Fated Fortune":
            return 2
        return None


def _service():
    return ExtremeArcanistFatedFortuneCriticalHealingService(
        skill_line_repository=_SkillLines()
    )


def _progression(rank=2):
    return CharacterProgression(
        passive_ranks={"Fated Fortune": rank},
        passive_cp_points={},
    )


def test_active_fated_fortune_adds_twelve_percent_critical_healing_for_seven_seconds():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Arcanist"),
        progression=_progression(),
        fated_fortune_active=True,
    )

    assert result.critical_healing_bonus == pytest.approx(0.12)
    assert result.duration_seconds == pytest.approx(7.0)
    assert result.unresolved == ()


def test_inactive_fated_fortune_does_not_add_critical_healing():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Arcanist"),
        progression=_progression(),
        fated_fortune_active=False,
    )

    assert result.critical_healing_bonus == pytest.approx(0.0)
    assert result.duration_seconds == pytest.approx(0.0)
    assert result.unresolved == ()


def test_missing_runtime_state_fails_closed_without_inventing_buff():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Arcanist"),
        progression=_progression(),
        fated_fortune_active=None,
    )

    assert result.critical_healing_bonus == pytest.approx(0.0)
    assert result.unresolved
    assert "explicit active buff-window state" in result.unresolved[0]


def test_explicit_route_can_remove_native_herald_of_the_tome():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="Arcanist",
            ClassSkillLines=["Curative Runeforms", "Soldier of Apocrypha", "Green Balance"],
        ),
        progression=_progression(),
        fated_fortune_active=True,
    )

    assert result.critical_healing_bonus == pytest.approx(0.0)
    assert result.unresolved == ()


def test_foreign_class_can_gain_fated_fortune_through_herald_subclass_route():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="Templar",
            ClassSkillLines=["Restoring Light", "Herald of the Tome", "Green Balance"],
        ),
        progression=_progression(),
        fated_fortune_active=True,
    )

    assert result.critical_healing_bonus == pytest.approx(0.12)
    assert result.unresolved == ()


def test_partial_fated_fortune_rank_fails_closed():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Arcanist"),
        progression=_progression(rank=1),
        fated_fortune_active=True,
    )

    assert result.critical_healing_bonus == pytest.approx(0.0)
    assert any("Partial passive rank is not yet modeled: Fated Fortune 1/2" in message for message in result.unresolved)


def test_non_boolean_runtime_state_is_rejected():
    with pytest.raises(ValueError, match="fated_fortune_active"):
        _service().resolve(
            build=PlayerBuild(EsoClass="Arcanist"),
            progression=_progression(),
            fated_fortune_active=1,
        )
