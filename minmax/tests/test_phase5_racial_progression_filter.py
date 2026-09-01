from ui.phase5_build_ui_support import _racial_skill_line_race


def test_racial_skill_line_classifier_matches_character_race_labels():
    races = {"breton", "nord", "high elf", "dark elf", "wood elf"}

    assert _racial_skill_line_race("Breton", races) == "breton"
    assert _racial_skill_line_race("Breton Skills", races) == "breton"
    assert _racial_skill_line_race("High Elf Racial", races) == "high elf"
    assert _racial_skill_line_race("Light Armor", races) is None
