from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_layer import BarId
from minmax.character_build.gear_piece import ArmorPiece, GearPieceCategory, GearSlot
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.role import Role


def _skill(index: int, skill_line_id: str, is_ultimate: bool = False) -> SlottedSkill:
    return SlottedSkill(
        skill_id=f"skill_{index}",
        skill_line_id=skill_line_id,
        is_ultimate=is_ultimate,
    )


def _bar(
    bar_id: BarId,
    weapon_type: WeaponType,
    off_hand: WeaponType | None,
    skill_line_id: str,
) -> Bar:
    slots = tuple(_skill(i, skill_line_id) for i in range(5)) + (
        _skill(5, skill_line_id, is_ultimate=True),
    )
    return Bar(
        bar_id=bar_id,
        main_hand=Weapon(weapon_type=weapon_type),
        off_hand=Weapon(weapon_type=off_hand) if off_hand else None,
        slots=slots,
    )


def _valid_warden_build() -> CharacterBuild:
    front = _bar(BarId.FRONT, WeaponType.RESTORATION_STAFF, None, "restoration_staff")
    back = _bar(BarId.BACK, WeaponType.FROST_STAFF, None, "destruction_staff")
    return CharacterBuild(
        name="Test Warden",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=front,
        back_bar=back,
    )


def test_valid_build_has_no_violations():
    build = _valid_warden_build()
    assert build.validate() == ()
    assert build.is_valid()


def test_one_mythic_maximum_is_enforced():
    build = _valid_warden_build()
    two_mythics = CharacterBuild(
        name="Illegal",
        character_class=build.character_class,
        role=build.role,
        mythic=ArmorPiece(
            slot=GearSlot.NECKLACE, category=GearPieceCategory.MYTHIC
        ),
        armor=(
            ArmorPiece(slot=GearSlot.RING_1, category=GearPieceCategory.MYTHIC),
        ),
        front_bar=build.front_bar,
        back_bar=build.back_bar,
    )
    violations = two_mythics.validate()
    assert any("at most one mythic" in problem for problem in violations)


def test_single_mythic_is_allowed():
    build = _valid_warden_build()
    one_mythic = CharacterBuild(
        name="Legal",
        character_class=build.character_class,
        role=build.role,
        mythic=ArmorPiece(
            slot=GearSlot.NECKLACE, category=GearPieceCategory.MYTHIC
        ),
        front_bar=build.front_bar,
        back_bar=build.back_bar,
    )
    assert one_mythic.validate() == ()


def test_pure_class_cannot_select_another_class_passive():
    front = _bar(BarId.FRONT, WeaponType.RESTORATION_STAFF, None, "ardent_flame")
    back = _bar(BarId.BACK, WeaponType.FROST_STAFF, None, "destruction_staff")
    build = CharacterBuild(
        name="Illegal Warden",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=front,
        back_bar=back,
    )
    violations = build.validate()
    assert any("belongs to dragonknight" in problem for problem in violations)


def test_weapon_determines_weapon_skill_line_access():
    # Skills claim dual_wield, but the bar is strung with a restoration staff.
    front = _bar(
        BarId.FRONT, WeaponType.RESTORATION_STAFF, None, "dual_wield"
    )
    back = _bar(BarId.BACK, WeaponType.FROST_STAFF, None, "destruction_staff")
    build = CharacterBuild(
        name="Illegal Weapon Access",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=front,
        back_bar=back,
    )
    violations = build.validate()
    assert any("only make 'restoration_staff' available" in problem for problem in violations)


def test_front_and_back_bar_may_legitimately_differ():
    """
    Front bar: Restoration Staff. Back bar: Destruction (Ice) Staff.
    This is the exact legitimate ESO pattern from the design brief.
    """
    build = _valid_warden_build()
    assert build.front_bar.weapon_skill_line.value == "restoration_staff"
    assert build.back_bar.weapon_skill_line.value == "destruction_staff"
    assert build.validate() == ()
