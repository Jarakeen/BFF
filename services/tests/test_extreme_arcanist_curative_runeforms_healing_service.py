from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_arcanist_curative_runeforms_healing_service import (
    ExtremeArcanistCurativeRuneformsHealingService,
)


class _SkillLines:
    @staticmethod
    def passive_max_rank(name: str):
        return 2 if name == "Healing Tides" else None


def _service():
    return ExtremeArcanistCurativeRuneformsHealingService(
        "fake.db",
        skill_line_repository=_SkillLines(),
    )


def _progression(rank=2):
    return CharacterProgression(
        passive_ranks={"Healing Tides": rank},
        passive_cp_points={},
    )


def test_healing_tides_scales_generic_healing_done_with_active_crux():
    service = _service()
    build = PlayerBuild(EsoClass="Arcanist")

    assert service.resolve(build=build, progression=_progression(), active_crux=0).multiplier == 1.0
    assert service.resolve(build=build, progression=_progression(), active_crux=1).multiplier == pytest.approx(1.04)
    assert service.resolve(build=build, progression=_progression(), active_crux=2).multiplier == pytest.approx(1.08)
    assert service.resolve(build=build, progression=_progression(), active_crux=3).multiplier == pytest.approx(1.12)


def test_healing_tides_requires_explicit_crux_state():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Arcanist"),
        progression=_progression(),
        active_crux=None,
    )

    assert result.multiplier == 1.0
    assert result.unresolved == ("Healing Tides requires explicit active Crux state",)


def test_healing_tides_rejects_impossible_crux_counts():
    with pytest.raises(ValueError, match="0 through 3"):
        _service().resolve(
            build=PlayerBuild(EsoClass="Arcanist"),
            progression=_progression(),
            active_crux=4,
        )
    with pytest.raises(ValueError, match="0 through 3"):
        _service().resolve(
            build=PlayerBuild(EsoClass="Arcanist"),
            progression=_progression(),
            active_crux=1.5,
        )


def test_explicit_subclass_route_can_remove_native_curative_runeforms():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="Arcanist",
            ClassSkillLines=["herald_of_the_tome", "soldier_of_apocrypha", "green_balance"],
        ),
        progression=_progression(),
        active_crux=3,
    )

    assert result.multiplier == 1.0
    assert result.unresolved == ()


def test_foreign_class_can_gain_healing_tides_through_curative_runeforms_route():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="Warden",
            ClassSkillLines=["green_balance", "curative_runeforms", "siphoning"],
        ),
        progression=_progression(),
        active_crux=3,
    )

    assert result.multiplier == pytest.approx(1.12)
    assert result.unresolved == ()


def test_partial_healing_tides_rank_is_blocked_instead_of_guessed():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Arcanist"),
        progression=_progression(rank=1),
        active_crux=3,
    )

    assert result.multiplier == 1.0
    assert result.unresolved == (
        "Partial passive rank is not yet modeled: Healing Tides 1/2",
    )
