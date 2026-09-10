from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_arcanist_harnessed_quintessence_service import (
    ExtremeArcanistHarnessedQuintessenceService,
)


class _SkillLines:
    @staticmethod
    def passive_max_rank(name):
        return 2 if name == "Harnessed Quintessence" else None


def _service():
    return ExtremeArcanistHarnessedQuintessenceService(
        "fake.db",
        skill_line_repository=_SkillLines(),
    )


def test_rank_two_active_window_grants_284_power():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Arcanist"),
        progression=CharacterProgression(passive_ranks={"Harnessed Quintessence": 2}),
        harnessed_quintessence_active=True,
    )

    assert result.weapon_spell_damage_bonus == 284.0
    assert result.duration_seconds == 10.0
    assert result.unresolved == ()


def test_rank_one_active_window_grants_142_power():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Arcanist"),
        progression=CharacterProgression(passive_ranks={"Harnessed Quintessence": 1}),
        harnessed_quintessence_active=True,
    )

    assert result.weapon_spell_damage_bonus == 142.0
    assert result.duration_seconds == 10.0
    assert result.unresolved == ()


def test_inactive_window_does_not_grant_power():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Arcanist"),
        progression=CharacterProgression(passive_ranks={"Harnessed Quintessence": 2}),
        harnessed_quintessence_active=False,
    )

    assert result.weapon_spell_damage_bonus == 0.0
    assert result.unresolved == ()


def test_missing_window_state_fails_closed():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Arcanist"),
        progression=CharacterProgression(passive_ranks={"Harnessed Quintessence": 2}),
        harnessed_quintessence_active=None,
    )

    assert result.weapon_spell_damage_bonus == 0.0
    assert result.unresolved == (
        "Harnessed Quintessence requires explicit active buff-window state",
    )


def test_explicit_subclass_route_can_remove_herald():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="Arcanist",
            ClassSkillLines=["Curative Runeforms", "Soldier of Apocrypha", "Green Balance"],
        ),
        progression=CharacterProgression(passive_ranks={"Harnessed Quintessence": 2}),
        harnessed_quintessence_active=True,
    )

    assert result.weapon_spell_damage_bonus == 0.0
    assert result.unresolved == ()


def test_foreign_class_can_gain_herald_route():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="Warden",
            ClassSkillLines=["Green Balance", "Winter's Embrace", "Herald of the Tome"],
        ),
        progression=CharacterProgression(passive_ranks={"Harnessed Quintessence": 2}),
        harnessed_quintessence_active=True,
    )

    assert result.weapon_spell_damage_bonus == 284.0
    assert result.unresolved == ()


def test_missing_passive_rank_fails_closed():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Arcanist"),
        progression=CharacterProgression(passive_ranks={}),
        harnessed_quintessence_active=True,
    )

    assert result.weapon_spell_damage_bonus == 0.0
    assert result.unresolved == (
        "Passive rank is not recorded for character: Harnessed Quintessence",
    )
