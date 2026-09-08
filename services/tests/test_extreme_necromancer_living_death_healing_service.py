from __future__ import annotations

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_necromancer_living_death_healing_service import (
    ExtremeNecromancerLivingDeathHealingService,
)


class _SkillLines:
    @staticmethod
    def passive_max_rank(name: str):
        return 2 if name == "Curative Curse" else None


def _progression(rank=2):
    return CharacterProgression(
        passive_ranks={"Curative Curse": rank},
        passive_cp_points={},
    )


def _service():
    return ExtremeNecromancerLivingDeathHealingService(
        skill_line_repository=_SkillLines()
    )


def test_pure_necromancer_gets_curative_curse_with_negative_effect():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Necromancer"),
        progression=_progression(),
        has_negative_effect=True,
    )

    assert result.multiplier == 1.12
    assert result.unresolved == ()


def test_curative_curse_does_not_apply_without_negative_effect():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Necromancer"),
        progression=_progression(),
        has_negative_effect=False,
    )

    assert result.multiplier == 1.0
    assert result.unresolved == ()


def test_curative_curse_requires_explicit_negative_effect_state():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Necromancer"),
        progression=_progression(),
        has_negative_effect=None,
    )

    assert result.multiplier == 1.0
    assert result.unresolved == (
        "Curative Curse requires explicit healer negative-effect state",
    )


def test_explicit_subclass_route_can_remove_native_living_death():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="Necromancer",
            ClassSkillLines=["Grave Lord", "Bone Tyrant", "Green Balance"],
        ),
        progression=_progression(),
        has_negative_effect=True,
    )

    assert result.multiplier == 1.0
    assert result.unresolved == ()


def test_foreign_class_can_gain_curative_curse_through_living_death_route():
    result = _service().resolve(
        build=PlayerBuild(
            EsoClass="Warden",
            ClassSkillLines=["Green Balance", "Winter's Embrace", "Living Death"],
        ),
        progression=_progression(),
        has_negative_effect=True,
    )

    assert result.multiplier == 1.12
    assert result.unresolved == ()


def test_partial_curative_curse_rank_is_blocked_instead_of_guessed():
    result = _service().resolve(
        build=PlayerBuild(EsoClass="Necromancer"),
        progression=_progression(rank=1),
        has_negative_effect=True,
    )

    assert result.multiplier == 1.0
    assert result.unresolved == (
        "Partial passive rank is not yet modeled: Curative Curse 1/2",
    )
