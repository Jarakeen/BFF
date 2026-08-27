from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.class_configuration import (
    ClassMasteryConfiguration,
    ClassSkillLineConfiguration,
)
from minmax.character_build.effect_layer import BarId
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.role import Role


def _bar(bar_id: BarId, skill_line_id: str) -> Bar:
    slots = tuple(
        SlottedSkill(
            skill_id=f"skill_{index}",
            skill_line_id=skill_line_id,
            is_ultimate=index == 5,
        )
        for index in range(6)
    )
    return Bar(
        bar_id=bar_id,
        main_hand=Weapon(weapon_type=WeaponType.RESTORATION_STAFF),
        off_hand=None,
        slots=slots,
    )


def _warden_build(class_lines: ClassSkillLineConfiguration) -> CharacterBuild:
    return CharacterBuild(
        name="Warden test",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        class_skill_lines=class_lines,
        front_bar=_bar(BarId.FRONT, "green_balance"),
        back_bar=_bar(BarId.BACK, "animal_companions"),
    )


def test_empty_class_line_selection_means_native_lines():
    config = ClassSkillLineConfiguration()
    assert set(config.effective_skill_lines(CharacterClass.WARDEN)) == {
        "animal_companions",
        "green_balance",
        "winters_embrace",
    }
    assert config.is_pure_class(CharacterClass.WARDEN)


def test_two_subclass_lines_are_allowed():
    config = ClassSkillLineConfiguration(
        equipped_skill_lines=(
            "green_balance",
            "storm_calling",
            "ardent_flame",
        )
    )
    assert config.validate(CharacterClass.WARDEN) == ()
    assert config.foreign_skill_lines(CharacterClass.WARDEN) == (
        "storm_calling",
        "ardent_flame",
    )
    assert not config.is_pure_class(CharacterClass.WARDEN)


def test_subclass_build_can_slot_equipped_foreign_class_line():
    config = ClassSkillLineConfiguration(
        equipped_skill_lines=(
            "green_balance",
            "winters_embrace",
            "storm_calling",
        )
    )
    build = _warden_build(config)
    build = CharacterBuild(
        name=build.name,
        character_class=build.character_class,
        role=build.role,
        class_skill_lines=config,
        front_bar=build.front_bar,
        back_bar=_bar(BarId.BACK, "storm_calling"),
    )
    assert build.validate() == ()


def test_three_foreign_lines_are_rejected():
    config = ClassSkillLineConfiguration(
        equipped_skill_lines=(
            "storm_calling",
            "ardent_flame",
            "shadow",
        )
    )
    violations = config.validate(CharacterClass.WARDEN)
    assert any("retain at least one native" in item for item in violations)
    assert any("at most 2" in item for item in violations)


def test_two_lines_from_same_foreign_class_are_rejected():
    config = ClassSkillLineConfiguration(
        equipped_skill_lines=(
            "green_balance",
            "storm_calling",
            "dark_magic",
        )
    )
    violations = config.validate(CharacterClass.WARDEN)
    assert any("at most one skill line from each foreign class" in item for item in violations)


def test_class_mastery_requires_pure_class_configuration():
    config = ClassSkillLineConfiguration(
        equipped_skill_lines=(
            "green_balance",
            "winters_embrace",
            "storm_calling",
        ),
        class_mastery=ClassMasteryConfiguration(passive_ability_ids=(1, 2)),
    )
    violations = config.validate(CharacterClass.WARDEN)
    assert any("cannot be selected while subclassing" in item for item in violations)


def test_class_mastery_requires_all_native_lines_mastered():
    config = ClassSkillLineConfiguration(
        class_mastery=ClassMasteryConfiguration(passive_ability_ids=(1, 2)),
    )
    build = _warden_build(config)
    assert not build.class_mastery_available
    assert any("has not mastered all three native" in item for item in build.validate())


def test_class_mastery_is_available_when_pure_and_all_native_lines_are_mastered():
    config = ClassSkillLineConfiguration(
        class_mastery=ClassMasteryConfiguration(passive_ability_ids=(1, 2)),
    )
    build = CharacterBuild(
        name="Mastery Warden",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        mastered_class_skill_lines=frozenset(
            {"animal_companions", "green_balance", "winters_embrace"}
        ),
        class_skill_lines=config,
        front_bar=_bar(BarId.FRONT, "green_balance"),
        back_bar=_bar(BarId.BACK, "animal_companions"),
    )
    assert build.class_mastery_available
    assert build.validate() == ()


def test_class_mastery_allows_at_most_two_passives():
    config = ClassSkillLineConfiguration(
        class_mastery=ClassMasteryConfiguration(passive_ability_ids=(1, 2, 3)),
    )
    assert any("at most 2" in item for item in config.validate(CharacterClass.WARDEN))
