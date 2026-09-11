import pytest

from minmax.armor_passive_input_resolver import ArmorPassiveInputResolver
from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_stat_inputs import GearCalculationInputs
from models.build_model import PlayerBuild


class _SkillLineRepository:
    def passive_max_rank(self, passive_name):
        if passive_name == "Juggernaut":
            return 2
        return None


def _five_heavy_two_light() -> PlayerBuild:
    build = PlayerBuild()
    weights = {
        "Head": "Heavy",
        "Shoulders": "Light",
        "Chest": "Heavy",
        "Hands": "Heavy",
        "Waist": "Light",
        "Legs": "Heavy",
        "Feet": "Heavy",
    }
    for slot, weight in weights.items():
        build.Armor[slot]["Weight"] = weight
    return build


def test_juggernaut_adds_two_percent_max_health_per_heavy_piece():
    result = ArmorPassiveInputResolver().apply(
        GearCalculationInputs(),
        _five_heavy_two_light(),
        juggernaut_owned=True,
    )

    contribution = result.health.skill_percent_contributions[-1]
    assert contribution.label == "Heavy Armor: Juggernaut"
    assert contribution.value == pytest.approx(0.10)
    assert result.applied_effect_count == 1


def test_juggernaut_requires_purchased_passive_even_with_heavy_armor_equipped():
    result = ArmorPassiveInputResolver().apply(
        GearCalculationInputs(),
        _five_heavy_two_light(),
        juggernaut_owned=False,
    )

    assert result.health.skill_percent_contributions == ()


def test_context_factory_gates_juggernaut_by_canonical_max_rank():
    build = _five_heavy_two_light()
    factory = BuildCalculationContextFactory(skill_line_repository=_SkillLineRepository())

    owned = factory.build(
        character_id="character",
        build_id="juggernaut",
        build=build,
        progression=CharacterProgression(
            owned_skill_lines=("Heavy Armor",),
            passive_ranks={"Juggernaut": 2},
        ),
    )
    absent = factory.build(
        character_id="character",
        build_id="no-juggernaut",
        build=build,
        progression=CharacterProgression(
            owned_skill_lines=("Heavy Armor",),
            passive_ranks={"Juggernaut": 0},
        ),
    )

    assert owned.character_state.max_health == 17600
    assert absent.character_state.max_health == 16000
