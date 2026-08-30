import pytest

from minmax.alliance_support_passive_input_resolver import AllianceSupportPassiveInputResolver
from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


class FakeSkillLineRepository:
    LINES = {
        "Barrier": "Support",
        "Revealing Flare": "Support",
        "Aggressive Horn": "Assault",
        "Echoing Vigor": "Assault",
    }

    def skill_line_for_ability_name(self, ability_name: str, *, class_name: str = "") -> str | None:
        _ = class_name
        return self.LINES.get(ability_name)


def _resolver() -> AllianceSupportPassiveInputResolver:
    return AllianceSupportPassiveInputResolver(FakeSkillLineRepository())


def test_magicka_aid_scales_per_support_ability_on_active_bar():
    build = PlayerBuild(FrontBarSkills=["Barrier", "Revealing Flare", "", "", "", ""])
    result = _resolver().apply(
        GearCalculationInputs(),
        build,
        active_bar="front",
        support_passives_owned=True,
    )
    contribution = result.magicka_recovery.skill_percent_contributions[-1]
    assert contribution.label == "Support: Magicka Aid"
    assert contribution.value == pytest.approx(0.20)


def test_magicka_aid_requires_explicit_support_ownership():
    build = PlayerBuild(FrontBarSkills=["Barrier", "", "", "", "", ""])
    original = GearCalculationInputs()
    assert _resolver().apply(original, build, active_bar="front") == original


def test_magicka_aid_ignores_assault_abilities_and_opposite_bar():
    build = PlayerBuild(
        FrontBarSkills=["Aggressive Horn", "Echoing Vigor", "", "", "", ""],
        BackBarSkills=["Barrier", "", "", "", "", ""],
    )
    front = _resolver().apply(
        GearCalculationInputs(),
        build,
        active_bar="front",
        support_passives_owned=True,
    )
    assert front.magicka_recovery.skill_percent_contributions == ()

    back = _resolver().apply(
        GearCalculationInputs(),
        build,
        active_bar="back",
        support_passives_owned=True,
    )
    assert back.magicka_recovery.skill_percent_contributions[-1].value == pytest.approx(0.10)


def test_context_factory_applies_owned_support_magicka_aid_to_final_recovery():
    build = PlayerBuild(FrontBarSkills=["Barrier", "", "", "", "", ""])
    context = BuildCalculationContextFactory(
        alliance_support_passive_resolver=_resolver(),
    ).build(
        character_id="support-test",
        build_id="support-build",
        build=build,
        progression=CharacterProgression(owned_skill_lines=("Support",)),
        active_bar="front",
    )

    assert context.character_state.magicka_recovery == 566
    trace = context.character_state.traces[StatId.MAGICKA_RECOVERY]
    assert "Support: Magicka Aid" in [step.label for step in trace.steps]
