from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


class EmptyGearSetRepository:
    def get_set(self, name):
        return None

    def get_set_by_id(self, set_id):
        return None

    def get_bonuses(self, set_id):
        return []


def test_gold_cp160_invigorating_piece_adds_all_three_recoveries():
    build = PlayerBuild()
    build.Armor["Chest"].update(
        {
            "Set": "Test Armor",
            "Weight": "Heavy",
            "Quality": "Gold",
            "Level": "CP160",
            "Trait": "Invigorating",
        }
    )

    context = BuildCalculationContextFactory(gear_set_repository=EmptyGearSetRepository()).build(
        character_id="char",
        build_id="invigorating",
        build=build,
        progression=CharacterProgression(),
    )

    for stat in (StatId.HEALTH_RECOVERY, StatId.MAGICKA_RECOVERY, StatId.STAMINA_RECOVERY):
        trace = context.character_state.traces[stat]
        assert any(
            step.label == "Chest: Invigorating (+16 recovery)" and step.value == 16
            for step in trace.steps
        )

    assert context.gear_effects_applied == 5
    assert not context.unresolved_gear_effects


def test_multiple_invigorating_pieces_remain_individually_traceable():
    build = PlayerBuild()
    for slot, weight in (("Head", "Light"), ("Hands", "Medium")):
        build.Armor[slot].update(
            {
                "Set": f"{slot} Set",
                "Weight": weight,
                "Quality": "Gold",
                "Level": "CP160",
                "Trait": "Invigorating",
            }
        )

    context = BuildCalculationContextFactory(gear_set_repository=EmptyGearSetRepository()).build(
        character_id="char",
        build_id="two-invigorating",
        build=build,
        progression=CharacterProgression(),
    )

    magicka = context.character_state.traces[StatId.MAGICKA_RECOVERY]
    labels = [step.label for step in magicka.steps]
    assert "Head: Invigorating (+16 recovery)" in labels
    assert "Hands: Invigorating (+16 recovery)" in labels
    assert context.character_state.magicka_recovery >= 32
