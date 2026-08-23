from enum import Enum


class CharacterClass(str, Enum):
    """
    A pure ESO class. This is a stable, named identity - it never carries
    a numeric value. What a class *means* mechanically (which skill lines
    it owns) is looked up separately via CLASS_SKILL_LINES, not stored on
    the enum member itself.
    """

    DRAGONKNIGHT = "dragonknight"
    SORCERER = "sorcerer"
    NIGHTBLADE = "nightblade"
    TEMPLAR = "templar"
    WARDEN = "warden"
    NECROMANCER = "necromancer"
    ARCANIST = "arcanist"


# Each class owns exactly three class skill lines. These are stable
# snake_case skill-line identities, not passives themselves - what each
# line grants is represented separately (see passive_grant.py).
#
# A pure class cannot arbitrarily select another class's passives: this
# registry is the single source of truth future code must check against
# before a build is allowed to claim a class-line passive or slot a
# class-line skill.
CLASS_SKILL_LINES: dict[CharacterClass, frozenset[str]] = {
    CharacterClass.DRAGONKNIGHT: frozenset(
        {"ardent_flame", "draconic_power", "earthen_heart"}
    ),
    CharacterClass.SORCERER: frozenset(
        {"dark_magic", "daedric_summoning", "storm_calling"}
    ),
    CharacterClass.NIGHTBLADE: frozenset(
        {"assassination", "shadow", "siphoning"}
    ),
    CharacterClass.TEMPLAR: frozenset(
        {"aedric_spear", "dawns_wrath", "restoring_light"}
    ),
    CharacterClass.WARDEN: frozenset(
        {"animal_companions", "green_balance", "winters_embrace"}
    ),
    CharacterClass.NECROMANCER: frozenset(
        {"grave_lord", "bone_tyrant", "living_death"}
    ),
    CharacterClass.ARCANIST: frozenset(
        {"herald_of_the_tome", "soldier_of_apocrypha", "curative_runeforms"}
    ),
}


def class_owns_skill_line(
    character_class: CharacterClass,
    skill_line_id: str,
) -> bool:
    """Does this class natively own the given class skill-line identity?"""
    return skill_line_id in CLASS_SKILL_LINES.get(character_class, frozenset())
