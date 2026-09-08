from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_nightblade_siphoning_healing_service import (
    ExtremeNightbladeSiphoningHealingService,
)


class _SkillLines:
    def __init__(self):
        self.lines = {
            "Funnel Health": "Siphoning",
            "Siphoning Attacks": "Siphoning",
            "Combat Prayer": "Restoration Staff",
            "Blue Betty": "Animal Companions",
        }

    def skill_line_for_ability_name(self, name):
        return self.lines.get(name)

    @staticmethod
    def passive_max_rank(name):
        return 2 if name == "Soul Siphoner" else None


def _service():
    return ExtremeNightbladeSiphoningHealingService(
        skill_line_repository=_SkillLines(),
    )


def test_soul_siphoner_counts_siphoning_skills_and_grants_generic_healing_done():
    build = PlayerBuild(
        BuildName="Nightblade Healer",
        EsoClass="nightblade",
        FrontBarSkills=[
            "Funnel Health",
            "Siphoning Attacks",
            "Combat Prayer",
            "",
            "",
            "",
        ],
    )
    progression = CharacterProgression(passive_ranks={"Soul Siphoner": 2})

    result = _service().resolve(
        build=build,
        progression=progression,
        active_bar="front",
    )

    assert result.siphoning_slots == 2
    assert result.multiplier == pytest.approx(1.06)
    assert result.unresolved == ()


def test_soul_siphoner_uses_selected_active_bar_only():
    build = PlayerBuild(
        EsoClass="nightblade",
        FrontBarSkills=["Combat Prayer", "", "", "", "", ""],
        BackBarSkills=["Funnel Health", "Siphoning Attacks", "", "", "", ""],
    )
    progression = CharacterProgression(passive_ranks={"Soul Siphoner": 2})

    front = _service().resolve(build=build, progression=progression, active_bar="front")
    back = _service().resolve(build=build, progression=progression, active_bar="back")

    assert front.multiplier == pytest.approx(1.0)
    assert front.siphoning_slots == 0
    assert back.multiplier == pytest.approx(1.06)
    assert back.siphoning_slots == 2


def test_explicit_subclass_route_removal_disables_native_nightblade_siphoning_passive():
    build = PlayerBuild(
        EsoClass="nightblade",
        ClassSkillLines=["assassination", "shadow", "green_balance"],
        FrontBarSkills=["Funnel Health", "", "", "", "", ""],
    )
    progression = CharacterProgression(passive_ranks={"Soul Siphoner": 2})

    result = _service().resolve(build=build, progression=progression)

    assert result.multiplier == pytest.approx(1.0)
    assert result.siphoning_slots == 0
    assert result.unresolved == ()


def test_foreign_siphoning_line_can_use_reviewed_passive_when_route_and_rank_are_explicit():
    build = PlayerBuild(
        EsoClass="warden",
        ClassSkillLines=["green_balance", "siphoning", "restoring_light"],
        FrontBarSkills=["Funnel Health", "Combat Prayer", "", "", "", ""],
    )
    progression = CharacterProgression(passive_ranks={"Soul Siphoner": 2})

    result = _service().resolve(build=build, progression=progression)

    assert result.multiplier == pytest.approx(1.03)
    assert result.siphoning_slots == 1
    assert result.unresolved == ()


def test_unknown_slot_line_preserves_known_soul_siphoner_lower_bound_and_blocker():
    build = PlayerBuild(
        EsoClass="nightblade",
        FrontBarSkills=["Funnel Health", "Mystery Skill", "", "", "", ""],
    )
    progression = CharacterProgression(passive_ranks={"Soul Siphoner": 2})

    result = _service().resolve(build=build, progression=progression)

    assert result.multiplier == pytest.approx(1.03)
    assert result.siphoning_slots == 1
    assert any("Mystery Skill" in message for message in result.unresolved)


def test_partial_soul_siphoner_rank_is_blocked_instead_of_guessed():
    build = PlayerBuild(
        EsoClass="nightblade",
        FrontBarSkills=["Funnel Health", "", "", "", "", ""],
    )
    progression = CharacterProgression(passive_ranks={"Soul Siphoner": 1})

    result = _service().resolve(build=build, progression=progression)

    assert result.multiplier == pytest.approx(1.0)
    assert result.siphoning_slots == 0
    assert result.unresolved == (
        "Partial passive rank is not yet modeled: Soul Siphoner 1/2",
    )
