from minmax.character_build.character_class import (
    CLASS_SKILL_LINES,
    CharacterClass,
    class_owns_skill_line,
)


def test_each_class_owns_exactly_three_lines():
    for character_class in CharacterClass:
        assert len(CLASS_SKILL_LINES[character_class]) == 3


def test_warden_owns_its_own_lines():
    assert class_owns_skill_line(CharacterClass.WARDEN, "animal_companions")
    assert class_owns_skill_line(CharacterClass.WARDEN, "winters_embrace")


def test_pure_class_cannot_own_another_class_line():
    assert not class_owns_skill_line(CharacterClass.WARDEN, "ardent_flame")
    assert not class_owns_skill_line(CharacterClass.DRAGONKNIGHT, "animal_companions")


def test_unknown_skill_line_is_not_owned():
    assert not class_owns_skill_line(CharacterClass.SORCERER, "not_a_real_line")
