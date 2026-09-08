from __future__ import annotations

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_templar_illuminate_combat_state_service import (
    ExtremeTemplarIlluminateCombatStateService,
)


class _SkillLines:
    @staticmethod
    def passive_max_rank(name):
        return 2 if name == "Illuminate" else None


def _service():
    return ExtremeTemplarIlluminateCombatStateService(
        "fake.db",
        skill_line_repository=_SkillLines(),
    )


def test_illuminate_grants_minor_sorcery_in_explicit_active_window():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=CharacterProgression(passive_ranks={"Illuminate": 2}),
        illuminate_window_active=True,
    )

    assert result.minor_sorcery_active
    assert result.combat_state.has_buff("Minor Sorcery")
    assert result.unresolved == ()


def test_illuminate_is_not_invented_without_explicit_window():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=CharacterProgression(passive_ranks={"Illuminate": 2}),
        illuminate_window_active=False,
    )

    assert not result.minor_sorcery_active
    assert not result.combat_state.active_buffs
    assert result.unresolved == ()


def test_rank_one_illuminate_can_supply_same_named_buff_in_shorter_active_window():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=CharacterProgression(passive_ranks={"Illuminate": 1}),
        illuminate_window_active=True,
    )

    assert result.minor_sorcery_active
    assert result.combat_state.has_buff("Minor Sorcery")
    assert result.unresolved == ()


def test_explicit_subclass_route_can_remove_native_illuminate():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="Templar",
            ClassSkillLines=["Aedric Spear", "Restoring Light", "Green Balance"],
        ),
        progression=CharacterProgression(passive_ranks={"Illuminate": 2}),
        illuminate_window_active=True,
    )

    assert not result.minor_sorcery_active
    assert not result.combat_state.has_buff("Minor Sorcery")
    assert result.unresolved == (
        "Illuminate scenario requires an equipped Dawn's Wrath class line",
    )


def test_foreign_class_can_gain_illuminate_through_dawns_wrath_route():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="Warden",
            ClassSkillLines=["Green Balance", "Winter's Embrace", "Dawn's Wrath"],
        ),
        progression=CharacterProgression(passive_ranks={"Illuminate": 2}),
        illuminate_window_active=True,
    )

    assert result.minor_sorcery_active
    assert result.combat_state.has_buff("Minor Sorcery")
    assert result.unresolved == ()


def test_unknown_illuminate_rank_preserves_unbuffed_state_and_blocker():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=CharacterProgression(passive_ranks=None),
        illuminate_window_active=True,
    )

    assert not result.minor_sorcery_active
    assert not result.combat_state.has_buff("Minor Sorcery")
    assert result.unresolved == ("Illuminate passive rank is not recorded",)


def test_missing_illuminate_rank_preserves_unbuffed_state_and_blocker():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=CharacterProgression(passive_ranks={}),
        illuminate_window_active=True,
    )

    assert not result.minor_sorcery_active
    assert not result.combat_state.has_buff("Minor Sorcery")
    assert result.unresolved == (
        "Passive rank is not recorded for character: Illuminate",
    )


def test_unlearned_illuminate_does_not_grant_minor_sorcery():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Templar"),
        progression=CharacterProgression(passive_ranks={"Illuminate": 0}),
        illuminate_window_active=True,
    )

    assert not result.minor_sorcery_active
    assert not result.combat_state.has_buff("Minor Sorcery")
    assert result.unresolved == ()
