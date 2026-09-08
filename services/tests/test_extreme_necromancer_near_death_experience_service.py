from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_necromancer_near_death_experience_service import (
    ExtremeNecromancerNearDeathExperienceService,
)


class _SkillLines:
    def __init__(self, mapping=None):
        self.mapping = dict(mapping or {})

    @staticmethod
    def passive_max_rank(name: str):
        return 2 if name == "Near-Death Experience" else None

    def skill_line_for_ability_name(self, name: str):
        return self.mapping.get(name)


def _progression(rank=2):
    return CharacterProgression(
        passive_ranks={"Near-Death Experience": rank},
        passive_cp_points={},
    )


def _service(mapping=None):
    return ExtremeNecromancerNearDeathExperienceService(
        skill_line_repository=_SkillLines(mapping)
    )


def test_near_death_experience_scales_healing_critical_chance_with_target_wounds():
    result = _service({"Spirit Guardian": "Living Death"}).resolve(
        build=PlayerBuild(
            EsoClass="Necromancer",
            FrontBarSkills=["Spirit Guardian", "", "", "", "", ""],
        ),
        progression=_progression(),
        target_health_fraction=0.25,
    )

    assert result.critical_chance_bonus == pytest.approx(0.09)
    assert result.living_death_slotted is True
    assert result.unresolved == ()


def test_near_death_experience_requires_living_death_on_active_bar():
    service = _service(
        {
            "Spirit Guardian": "Living Death",
            "Combat Prayer": "Restoration Staff",
        }
    )
    build = PlayerBuild(
        EsoClass="Necromancer",
        FrontBarSkills=["Combat Prayer", "", "", "", "", ""],
        BackBarSkills=["Spirit Guardian", "", "", "", "", ""],
    )

    front = service.resolve(
        build=build,
        progression=_progression(),
        target_health_fraction=0.25,
        active_bar="front",
    )
    back = service.resolve(
        build=build,
        progression=_progression(),
        target_health_fraction=0.25,
        active_bar="back",
    )

    assert front.critical_chance_bonus == 0.0
    assert front.living_death_slotted is False
    assert front.unresolved == ()
    assert back.critical_chance_bonus == pytest.approx(0.09)
    assert back.living_death_slotted is True
    assert back.unresolved == ()


def test_explicit_route_can_remove_native_near_death_experience_access():
    result = _service({"Spirit Guardian": "Living Death"}).resolve(
        build=PlayerBuild(
            EsoClass="Necromancer",
            ClassSkillLines=["Grave Lord", "Bone Tyrant", "Green Balance"],
            FrontBarSkills=["Spirit Guardian", "", "", "", "", ""],
        ),
        progression=_progression(),
        target_health_fraction=0.25,
    )

    assert result.critical_chance_bonus == 0.0
    assert result.living_death_slotted is False
    assert result.unresolved == ()


def test_foreign_class_can_gain_near_death_experience_through_living_death_route():
    result = _service({"Spirit Guardian": "Living Death"}).resolve(
        build=PlayerBuild(
            EsoClass="Warden",
            ClassSkillLines=["Green Balance", "Winter's Embrace", "Living Death"],
            FrontBarSkills=["Spirit Guardian", "", "", "", "", ""],
        ),
        progression=_progression(),
        target_health_fraction=0.50,
    )

    assert result.critical_chance_bonus == pytest.approx(0.06)
    assert result.living_death_slotted is True
    assert result.unresolved == ()


def test_unknown_slot_blocks_only_when_living_death_slot_condition_is_unproven():
    result = _service({}).resolve(
        build=PlayerBuild(
            EsoClass="Necromancer",
            FrontBarSkills=["Mystery Skill", "", "", "", "", ""],
        ),
        progression=_progression(),
        target_health_fraction=0.25,
    )

    assert result.critical_chance_bonus == 0.0
    assert result.living_death_slotted is False
    assert result.unresolved == (
        "Near-Death Experience slot condition: could not resolve canonical skill line "
        "for slotted ability 'Mystery Skill' on front bar",
    )


def test_proven_living_death_slot_makes_other_unknown_slot_irrelevant_to_trigger():
    result = _service({"Spirit Guardian": "Living Death"}).resolve(
        build=PlayerBuild(
            EsoClass="Necromancer",
            FrontBarSkills=["Spirit Guardian", "Mystery Skill", "", "", "", ""],
        ),
        progression=_progression(),
        target_health_fraction=0.25,
    )

    assert result.critical_chance_bonus == pytest.approx(0.09)
    assert result.living_death_slotted is True
    assert result.unresolved == ()


def test_near_death_experience_requires_explicit_target_health_once_triggered():
    result = _service({"Spirit Guardian": "Living Death"}).resolve(
        build=PlayerBuild(
            EsoClass="Necromancer",
            FrontBarSkills=["Spirit Guardian", "", "", "", "", ""],
        ),
        progression=_progression(),
        target_health_fraction=None,
    )

    assert result.critical_chance_bonus == 0.0
    assert result.living_death_slotted is True
    assert result.unresolved == (
        "Near-Death Experience requires explicit target-health state for healing critical chance",
    )


def test_partial_near_death_experience_rank_is_blocked_instead_of_guessed():
    result = _service({"Spirit Guardian": "Living Death"}).resolve(
        build=PlayerBuild(
            EsoClass="Necromancer",
            FrontBarSkills=["Spirit Guardian", "", "", "", "", ""],
        ),
        progression=_progression(rank=1),
        target_health_fraction=0.25,
    )

    assert result.critical_chance_bonus == 0.0
    assert result.living_death_slotted is True
    assert result.unresolved == (
        "Partial passive rank is not yet modeled: Near-Death Experience 1/2",
    )
