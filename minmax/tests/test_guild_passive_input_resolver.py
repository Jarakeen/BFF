import pytest

from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.guild_passive_input_resolver import GuildPassiveInputResolver
from models.build_model import PlayerBuild


class FakeSkillLineRepository:
    LINES = {
        "Inner Light": "Mages Guild",
        "Entropy": "Mages Guild",
        "Barbed Trap": "Fighters Guild",
        "Dawnbreaker of Smiting": "Fighters Guild",
        "Combat Prayer": "Restoration Staff",
    }

    def skill_line_for_ability_name(self, ability_name: str, *, class_name: str = "") -> str | None:
        _ = class_name
        return self.LINES.get(ability_name)


def _resolver() -> GuildPassiveInputResolver:
    return GuildPassiveInputResolver(FakeSkillLineRepository())


def test_magicka_controller_scales_per_slotted_mages_guild_ability():
    build = PlayerBuild(FrontBarSkills=["Inner Light", "Entropy", "Combat Prayer", "", "", ""])
    result = _resolver().apply(
        GearCalculationInputs(),
        build,
        active_bar="front",
        mages_guild_passives_owned=True,
    )

    assert result.magicka.skill_percent_contributions[-1].label == "Mages Guild: Magicka Controller"
    assert result.magicka.skill_percent_contributions[-1].value == pytest.approx(0.04)
    assert result.magicka_recovery.skill_percent_contributions[-1].value == pytest.approx(0.04)


def test_slayer_scales_per_slotted_fighters_guild_ability():
    build = PlayerBuild(FrontBarSkills=["Barbed Trap", "Dawnbreaker of Smiting", "", "", "", ""])
    result = _resolver().apply(
        GearCalculationInputs(),
        build,
        active_bar="front",
        fighters_guild_passives_owned=True,
    )

    assert result.core.weapon_damage.percent[-1].label == "Fighters Guild: Slayer"
    assert result.core.weapon_damage.percent[-1].value == pytest.approx(0.06)
    assert result.core.spell_damage.percent[-1].value == pytest.approx(0.06)


def test_guild_passives_require_explicit_ownership():
    build = PlayerBuild(FrontBarSkills=["Inner Light", "Barbed Trap", "", "", "", ""])
    original = GearCalculationInputs()
    assert _resolver().apply(original, build, active_bar="front") == original


def test_guild_passives_use_only_active_bar_slots():
    build = PlayerBuild(
        FrontBarSkills=["Combat Prayer", "", "", "", "", ""],
        BackBarSkills=["Inner Light", "Barbed Trap", "", "", "", ""],
    )
    front = _resolver().apply(
        GearCalculationInputs(),
        build,
        active_bar="front",
        mages_guild_passives_owned=True,
        fighters_guild_passives_owned=True,
    )
    back = _resolver().apply(
        GearCalculationInputs(),
        build,
        active_bar="back",
        mages_guild_passives_owned=True,
        fighters_guild_passives_owned=True,
    )

    assert front.magicka.skill_percent_contributions == ()
    assert front.core.weapon_damage.percent == ()
    assert back.magicka.skill_percent_contributions[-1].value == pytest.approx(0.02)
    assert back.core.weapon_damage.percent[-1].value == pytest.approx(0.03)
