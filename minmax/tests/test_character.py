from minmax.character_build.character import Character
from minmax.character_build.character_class import CharacterClass
from minmax.role import Role


def test_character_is_persistent_identity_not_a_build():
    character = Character(
        character_id="char-1",
        name="Test Warden",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        race_id=1,
        mastered_class_skill_lines=frozenset(
            {"animal_companions", "green_balance", "winters_embrace"}
        ),
    )
    assert character.character_id == "char-1"
    assert character.name == "Test Warden"
    assert character.has_mastered_skill_line("green_balance")
    assert character.validate() == ()


def test_character_cannot_be_both_vampire_and_werewolf():
    character = Character(
        character_id="char-2",
        name="Illegal",
        character_class=CharacterClass.NIGHTBLADE,
        role=Role.DD,
        vampire=True,
        werewolf=True,
    )
    assert any("both Vampire and Werewolf" in item for item in character.validate())
