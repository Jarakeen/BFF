from models.build_model import PlayerBuild
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.warden_passive_input_resolver import WardenPassiveInputResolver


class FakeSkillLineRepository:
    LINES = {
        "Eternal Guardian": "Animal Companions",
        "Budding Seeds": "Green Balance",
        "Combat Prayer": "Restoration Staff",
        "Winter's Revenge": "Winter's Embrace",
        "Expansive Frost Cloak": "Winter's Embrace",
        "Aggressive Horn": "Assault",
    }

    def skill_line_for_ability_name(self, ability_name: str, *, class_name: str = "") -> str | None:
        _ = class_name
        return self.LINES.get(ability_name)


def _resolver() -> WardenPassiveInputResolver:
    return WardenPassiveInputResolver(FakeSkillLineRepository())


def test_front_bar_warden_passives_use_only_front_bar_skill_lines():
    build = PlayerBuild(
        EsoClass="Warden",
        FrontBarSkills=["Budding Seeds", "Combat Prayer", "Eternal Guardian", "", "", ""],
        BackBarSkills=["Winter's Revenge", "Expansive Frost Cloak", "Aggressive Horn", "", "", ""],
    )

    result = _resolver().apply(GearCalculationInputs(), build, active_bar="front")

    assert [c.label for c in result.magicka_recovery.skill_percent_contributions] == ["Warden: Flourish"]
    assert result.magicka_recovery.skill_percent_contributions[0].value == 0.20
    assert result.stamina_recovery.skill_percent_contributions[0].value == 0.20
    assert result.core.critical_damage.additive_after_percent[-1].label == "Warden: Advanced Species"
    assert result.core.critical_damage.additive_after_percent[-1].value == 0.05
    assert result.core.physical_resistance.flat == ()
    assert result.core.spell_resistance.flat == ()


def test_back_bar_warden_passives_do_not_carry_front_bar_flourish_or_advanced_species():
    build = PlayerBuild(
        EsoClass="Warden",
        FrontBarSkills=["Eternal Guardian", "", "", "", "", ""],
        BackBarSkills=["Winter's Revenge", "Expansive Frost Cloak", "Aggressive Horn", "", "", ""],
    )

    result = _resolver().apply(GearCalculationInputs(), build, active_bar="back")

    assert result.magicka_recovery.skill_percent_contributions == ()
    assert result.stamina_recovery.skill_percent_contributions == ()
    assert result.core.critical_damage.additive_after_percent == ()
    assert result.core.physical_resistance.flat[-1].label == "Warden: Frozen Armor"
    assert result.core.physical_resistance.flat[-1].value == 2480.0
    assert result.core.spell_resistance.flat[-1].value == 2480.0


def test_non_warden_build_is_unchanged():
    build = PlayerBuild(EsoClass="Templar", FrontBarSkills=["Eternal Guardian", "", "", "", "", ""])
    original = GearCalculationInputs()

    assert _resolver().apply(original, build, active_bar="front") == original
