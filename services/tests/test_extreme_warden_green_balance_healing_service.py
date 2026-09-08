from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_warden_green_balance_healing_service import (
    ExtremeWardenGreenBalanceHealingService,
)


class _SkillLines:
    def __init__(self, *, line_by_name=None, max_rank=2):
        self.line_by_name = dict(line_by_name or {})
        self.max_rank = max_rank

    def skill_line_for_ability_name(self, name):
        return self.line_by_name.get(name)

    def passive_max_rank(self, name):
        return self.max_rank if name == "Emerald Moss" else None


def test_emerald_moss_scales_green_balance_heal_by_each_active_bar_green_balance_slot():
    service = ExtremeWardenGreenBalanceHealingService(
        skill_line_repository=_SkillLines(
            line_by_name={
                "Budding Seeds": "Green Balance",
                "Enchanted Growth": "Green Balance",
                "Blue Betty": "Animal Companions",
            }
        )
    )
    build = PlayerBuild(
        BuildName="Warden Healer",
        EsoClass="warden",
        FrontBarSkills=[
            "Budding Seeds",
            "Enchanted Growth",
            "Blue Betty",
            "",
            "",
            "",
        ],
    )
    progression = CharacterProgression(passive_ranks={"Emerald Moss": 2})

    result = service.resolve(
        build=build,
        progression=progression,
        ability_name="Budding Seeds",
        active_bar="front",
    )

    assert result.green_balance_slots == 2
    assert result.multiplier == pytest.approx(1.10)
    assert result.unresolved == ()


def test_emerald_moss_applies_to_explicit_foreign_green_balance_subclass_route():
    service = ExtremeWardenGreenBalanceHealingService(
        skill_line_repository=_SkillLines(
            line_by_name={"Budding Seeds": "Green Balance"}
        )
    )
    build = PlayerBuild(
        BuildName="Subclass Healer",
        EsoClass="templar",
        ClassSkillLines=["aedric_spear", "restoring_light", "green_balance"],
        FrontBarSkills=["Budding Seeds", "", "", "", "", ""],
    )
    progression = CharacterProgression(passive_ranks={"Emerald Moss": 2})

    result = service.resolve(
        build=build,
        progression=progression,
        ability_name="Budding Seeds",
    )

    assert result.green_balance_slots == 1
    assert result.multiplier == pytest.approx(1.05)
    assert result.unresolved == ()


def test_emerald_moss_does_not_survive_route_that_does_not_equip_green_balance():
    service = ExtremeWardenGreenBalanceHealingService(
        skill_line_repository=_SkillLines(
            line_by_name={"Budding Seeds": "Green Balance"}
        )
    )
    build = PlayerBuild(
        BuildName="No Green Balance",
        EsoClass="warden",
        ClassSkillLines=["animal_companions", "winters_embrace", "restoring_light"],
        FrontBarSkills=["Budding Seeds", "", "", "", "", ""],
    )
    progression = CharacterProgression(passive_ranks={"Emerald Moss": 2})

    result = service.resolve(
        build=build,
        progression=progression,
        ability_name="Budding Seeds",
    )

    assert result.multiplier == pytest.approx(1.0)
    assert result.green_balance_slots == 0
    assert result.unresolved == ()


def test_emerald_moss_missing_rank_and_unknown_slot_identity_preserve_blockers():
    service = ExtremeWardenGreenBalanceHealingService(
        skill_line_repository=_SkillLines(
            line_by_name={"Budding Seeds": "Green Balance"}
        )
    )
    build = PlayerBuild(
        BuildName="Unknown Passive",
        EsoClass="warden",
        FrontBarSkills=["Budding Seeds", "Mystery Skill", "", "", "", ""],
    )

    missing_rank = service.resolve(
        build=build,
        progression=CharacterProgression(passive_ranks={}),
        ability_name="Budding Seeds",
    )
    assert missing_rank.multiplier == pytest.approx(1.0)
    assert "Passive rank is not recorded for character: Emerald Moss" in missing_rank.unresolved

    resolved_rank = service.resolve(
        build=build,
        progression=CharacterProgression(passive_ranks={"Emerald Moss": 2}),
        ability_name="Budding Seeds",
    )
    assert resolved_rank.green_balance_slots == 1
    assert resolved_rank.multiplier == pytest.approx(1.05)
    assert any("Mystery Skill" in message for message in resolved_rank.unresolved)
