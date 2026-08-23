from enum import Enum


class WeaponType(str, Enum):
    """
    The physical weapon type equipped in a hand slot. This is a stable
    identity - it never carries damage/trait/enchant magnitude, those
    live on the Weapon instance that references this type (see weapon.py).
    """

    SWORD = "sword"
    AXE = "axe"
    MACE = "mace"
    DAGGER = "dagger"
    SHIELD = "shield"
    GREATSWORD = "greatsword"
    BATTLEAXE = "battleaxe"
    MAUL = "maul"
    BOW = "bow"
    RESTORATION_STAFF = "restoration_staff"
    FROST_STAFF = "frost_staff"
    FLAME_STAFF = "flame_staff"
    LIGHTNING_STAFF = "lightning_staff"
    NONE = "none"
    """No weapon equipped in this hand (e.g. empty off-hand)."""


class WeaponSkillLine(str, Enum):
    """
    The weapon skill line a bar's equipped weapon(s) make available.

    A weapon skill line is a property of the *bar's weapon configuration*,
    not of a single weapon type in isolation - e.g. a sword only grants
    One Hand and Shield when paired with a shield, and grants Dual Wield
    when paired with a second one-handed weapon.
    """

    ONE_HAND_AND_SHIELD = "one_hand_and_shield"
    DUAL_WIELD = "dual_wield"
    TWO_HANDED = "two_handed"
    BOW = "bow"
    DESTRUCTION_STAFF = "destruction_staff"
    RESTORATION_STAFF = "restoration_staff"


_ONE_HANDED = frozenset(
    {
        WeaponType.SWORD,
        WeaponType.AXE,
        WeaponType.MACE,
        WeaponType.DAGGER,
    }
)

_TWO_HANDED = frozenset(
    {WeaponType.GREATSWORD, WeaponType.BATTLEAXE, WeaponType.MAUL}
)

_DESTRO_STAVES = frozenset(
    {WeaponType.FROST_STAFF, WeaponType.FLAME_STAFF, WeaponType.LIGHTNING_STAFF}
)


def resolve_weapon_skill_line(
    main_hand: WeaponType,
    off_hand: WeaponType = WeaponType.NONE,
) -> WeaponSkillLine:
    """
    Determine which weapon skill line a specific bar's weapon configuration
    makes available. This is what "weapon type determines which weapon
    skill line is available on that bar" resolves to mechanically.

    Raises ValueError for a configuration that ESO does not allow, rather
    than silently guessing a skill line.
    """
    if main_hand in _TWO_HANDED and off_hand == WeaponType.NONE:
        return WeaponSkillLine.TWO_HANDED

    if main_hand == WeaponType.BOW and off_hand == WeaponType.NONE:
        return WeaponSkillLine.BOW

    if main_hand == WeaponType.RESTORATION_STAFF and off_hand == WeaponType.NONE:
        return WeaponSkillLine.RESTORATION_STAFF

    if main_hand in _DESTRO_STAVES and off_hand == WeaponType.NONE:
        return WeaponSkillLine.DESTRUCTION_STAFF

    if main_hand in _ONE_HANDED and off_hand == WeaponType.SHIELD:
        return WeaponSkillLine.ONE_HAND_AND_SHIELD

    if main_hand in _ONE_HANDED and off_hand in _ONE_HANDED:
        return WeaponSkillLine.DUAL_WIELD

    raise ValueError(
        f"No valid ESO weapon skill line for main_hand={main_hand!r}, "
        f"off_hand={off_hand!r}."
    )
