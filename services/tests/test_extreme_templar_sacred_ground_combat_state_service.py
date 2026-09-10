from __future__ import annotations

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_templar_sacred_ground_combat_state_service import (
    ExtremeTemplarSacredGroundCombatStateService,
)


class _SkillLines:
    @staticmethod
    def passive_max_rank(name):
        return 2 if name == "Sacred Ground" else None


def _service():
    return ExtremeTemplarSacredGroundCombatStateService(
        "fake.db",
        skill_line_repository=_SkillLines(),
    )


def test_sacred_ground_grants_minor_mending_in_explicit_active_window():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=CharacterProgression(passive_ranks={"Sacred Ground": 2}),
        sacred_ground_window_active=True,
    )

    assert result.minor_mending_active
    assert result.combat_state.has_buff("Minor Mending")
    assert result.unresolved == ()


def test_sacred_ground_rank_one_also_grants_minor_mending_in_proven_window():
    service = _service()
    result = service.resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=CharacterProgression(passive_ranks={"Sacred Ground": 1}),
        sacred_ground_window_active=True,
    )

    assert service.GRACE_SECONDS_BY_RANK == {1: 2.0, 2: 4.0}
    assert result.minor_mending_active
    assert result.combat_state.has_buff("Minor Mending")
    assert result.unresolved == ()


def test_sacred_ground_is_not_invented_without_explicit_window():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=CharacterProgression(passive_ranks={"Sacred Ground": 2}),
        sacred_ground_window_active=False,
    )

    assert not result.minor_mending_active
    assert not result.combat_state.active_buffs
    assert result.unresolved == ()


def test_explicit_subclass_route_can_remove_native_sacred_ground():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="Templar",
            ClassSkillLines=["Aedric Spear", "Dawn's Wrath", "Green Balance"],
        ),
        progression=CharacterProgression(passive_ranks={"Sacred Ground": 2}),
        sacred_ground_window_active=True,
    )

    assert not result.minor_mending_active
    assert not result.combat_state.has_buff("Minor Mending")
    assert result.unresolved == (
        "Sacred Ground scenario requires an equipped Restoring Light class line",
    )


def test_foreign_class_can_gain_sacred_ground_through_restoring_light_route():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="Warden",
            ClassSkillLines=["Green Balance", "Winter's Embrace", "Restoring Light"],
        ),
        progression=CharacterProgression(passive_ranks={"Sacred Ground": 2}),
        sacred_ground_window_active=True,
    )

    assert result.minor_mending_active
    assert result.combat_state.has_buff("Minor Mending")
    assert result.unresolved == ()


def test_unknown_sacred_ground_rank_preserves_unbuffed_state_and_blocker():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=CharacterProgression(passive_ranks=None),
        sacred_ground_window_active=True,
    )

    assert not result.minor_mending_active
    assert not result.combat_state.has_buff("Minor Mending")
    assert result.unresolved == ("Sacred Ground passive rank is not recorded",)
