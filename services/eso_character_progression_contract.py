from __future__ import annotations

"""Source-backed ESO base character/progression contract.

This module describes *legality and progression*, not combat-effect math. It is
intended as a shared rules layer for Extreme Builds, Comp Maker, saved-build
validation, progression UI, and rotation planning.

Boundaries:
- Join these rules to canonical skills/ranks/effects in ``eso.db``.
- Do not infer skill effects from names or from this file.
- Subclassing and Class Mastery are mutually exclusive character routes.
- Ultimate and Crux are runtime resources, not static sheet bonuses.
- Champion progression is intentionally outside the normal-level 1-50 contract.

Source snapshots reviewed 2026-09-07:
- UESP Online:Attributes r2861719
- UESP Online:Health r2861707
- UESP Online:Magicka r2861709
- UESP Online:Stamina r3044713
- UESP Online:Skills r3600114
- UESP Online:Ultimate r3543403
- UESP Online:Crux r3559618
- UESP Online:Class Mastery r3581024
- ESO-Hub Subclassing guide, modified 2026-05-20

Re-review this contract when an ESO update changes base progression,
subclassing, Class Mastery, bar rules, or runtime-resource behavior.
"""

from dataclasses import dataclass
from enum import Enum

from services.skill_bar_eligibility import CLASS_SKILL_LINES


class AttributeKey(str, Enum):
    HEALTH = "health"
    MAGICKA = "magicka"
    STAMINA = "stamina"


@dataclass(frozen=True)
class CharacterProgressionRules:
    minimum_level: int = 1
    normal_level_cap: int = 50
    attribute_points_at_level_50: int = 64
    weapon_swap_unlock_level: int = 15
    normal_skill_slots_per_bar: int = 5
    ultimate_slots_per_bar: int = 1
    bars_after_weapon_swap: int = 2
    active_skill_ranks_before_morph: int = 4
    active_skill_ranks_after_morph: int = 4
    morph_choices: int = 2


CHARACTER_RULES = CharacterProgressionRules()


@dataclass(frozen=True)
class BaseAttributeRule:
    key: AttributeKey
    level_coefficient: float
    base_constant: float
    per_attribute_point: float
    level_50_unallocated: float
    level_50_all_64_points: float

    def value(self, *, level: int, attribute_points: int) -> float:
        validate_character_level(level)
        points = int(attribute_points)
        if points < 0:
            raise ValueError("attribute_points cannot be negative")
        if points > CHARACTER_RULES.attribute_points_at_level_50:
            raise ValueError("attribute_points exceed the level-50 allocation ceiling")
        return self.level_coefficient * int(level) + self.base_constant + self.per_attribute_point * points


BASE_ATTRIBUTES = {
    AttributeKey.HEALTH: BaseAttributeRule(
        AttributeKey.HEALTH, 300.0, 1000.0, 122.0, 16000.0, 23808.0
    ),
    AttributeKey.MAGICKA: BaseAttributeRule(
        AttributeKey.MAGICKA, 220.0, 1000.0, 111.0, 12000.0, 19104.0
    ),
    AttributeKey.STAMINA: BaseAttributeRule(
        AttributeKey.STAMINA, 220.0, 1000.0, 111.0, 12000.0, 19104.0
    ),
}


@dataclass(frozen=True)
class SkillProgressionRules:
    passive_upgrade_costs_skill_point: bool = True
    morph_costs_skill_point: bool = True
    active_skill_progresses_through_use: bool = True
    class_line_requires_slotted_class_skill_for_xp: bool = True
    weapon_line_can_progress_from_matching_weapon_equipped: bool = True
    weapon_line_progress_accelerated_by_slotted_weapon_skills: bool = True
    armor_line_requires_matching_armor_piece: bool = True
    armor_line_progress_accelerated_by_more_matching_pieces: bool = True
    racial_line_unlock_level: int = 5


SKILL_PROGRESSION_RULES = SkillProgressionRules()

WEAPON_SKILL_LINES = frozenset(
    {
        "two handed",
        "one hand and shield",
        "dual wield",
        "bow",
        "destruction staff",
        "restoration staff",
    }
)
ARMOR_SKILL_LINES = frozenset({"light armor", "medium armor", "heavy armor"})


@dataclass(frozen=True)
class UltimateRules:
    maximum_resource: int = 500
    one_ultimate_per_bar: bool = True
    normal_cast_consumes_accumulated_resource: bool = True
    standard_regen_buff_seconds: float = 9.0
    standard_regen_per_second: float = 3.0
    standard_regen_total: float = 27.0
    trigger_light_or_heavy_attack: bool = True
    trigger_heal_other: bool = True
    trigger_self_heal: bool = False
    trigger_block: bool = True
    trigger_dodge: bool = True


ULTIMATE_RULES = UltimateRules()


@dataclass(frozen=True)
class CruxRules:
    owner_class: str = "Arcanist"
    maximum_stacks: int = 3
    generation_requires_combat: bool = True
    out_of_combat_expiry_seconds: float = 30.0
    generators_at_cap_have_no_effect: bool = True
    generation_triggered_passives_fire_at_cap: bool = False
    consumers_consume_all_current_crux: bool = True
    consumers_castable_at_zero_crux: bool = True


CRUX_RULES = CruxRules()


@dataclass(frozen=True)
class SubclassingRules:
    account_unlock_character_level: int = 50
    introductory_quest: str = "A Study in Discipline"
    original_class_lines_total: int = 3
    minimum_original_class_lines_retained: int = 1
    maximum_foreign_class_lines_equipped: int = 2
    total_equipped_class_lines: int = 3
    grants_full_selected_line_skills_morphs_passives: bool = True
    line_rank_cap: int = 50
    account_mastered_rank: int = 50
    maximum_unmastered_leveling_slots: int = 3
    subclass_skill_or_passive_cost: int = 2
    total_skill_points_per_subclass_line: int = 40
    mastered_lines_swappable_without_leveling_slot: bool = True
    class_mastery_allowed: bool = False


SUBCLASSING_RULES = SubclassingRules()


@dataclass(frozen=True)
class ClassMasteryRules:
    classes_supported: int = 7
    passives_per_class: int = 5
    selectable_passives: int = 2
    requires_all_three_native_class_lines_rank: int = 50
    allowed_while_subclassing: bool = False


CLASS_MASTERY_RULES = ClassMasteryRules()


@dataclass(frozen=True)
class ClassRouteValidation:
    legal: bool
    errors: tuple[str, ...]


def _key(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def validate_character_level(level: int) -> None:
    value = int(level)
    if value < CHARACTER_RULES.minimum_level:
        raise ValueError("character level must be at least 1")
    if value > CHARACTER_RULES.normal_level_cap:
        raise ValueError("normal character-level contract ends at 50; Champion progression is separate")


def validate_attribute_allocation(*, health: int, magicka: int, stamina: int) -> None:
    values = (int(health), int(magicka), int(stamina))
    if any(value < 0 for value in values):
        raise ValueError("attribute allocations cannot be negative")
    if sum(values) > CHARACTER_RULES.attribute_points_at_level_50:
        raise ValueError("attribute allocations exceed 64 points")


def base_attribute_value(
    attribute: AttributeKey | str,
    *,
    level: int,
    attribute_points: int,
) -> float:
    key = AttributeKey(str(getattr(attribute, "value", attribute)).strip().casefold())
    return BASE_ATTRIBUTES[key].value(level=level, attribute_points=attribute_points)


def available_bar_count(character_level: int) -> int:
    validate_character_level(character_level)
    return 2 if int(character_level) >= CHARACTER_RULES.weapon_swap_unlock_level else 1


def validate_bar_shape(
    *, normal_skill_count: int, ultimate_count: int, character_level: int = 50
) -> None:
    validate_character_level(character_level)
    normals = int(normal_skill_count)
    ultimates = int(ultimate_count)
    if normals < 0 or ultimates < 0:
        raise ValueError("slot counts cannot be negative")
    if normals > CHARACTER_RULES.normal_skill_slots_per_bar:
        raise ValueError("a skill bar cannot contain more than five normal skills")
    if ultimates > CHARACTER_RULES.ultimate_slots_per_bar:
        raise ValueError("a skill bar cannot contain more than one Ultimate")


def validate_subclass_route(
    *, base_class: str, equipped_class_lines: tuple[str, ...]
) -> ClassRouteValidation:
    base = _key(base_class)
    native = CLASS_SKILL_LINES.get(base)
    errors: list[str] = []
    if native is None:
        return ClassRouteValidation(False, (f"unknown base class: {base_class}",))

    equipped = tuple(_key(line) for line in equipped_class_lines if _key(line))
    if len(equipped) != SUBCLASSING_RULES.total_equipped_class_lines:
        errors.append("a subclass route must equip exactly three class skill lines")
    if len(set(equipped)) != len(equipped):
        errors.append("equipped class skill lines must be distinct")

    retained = sum(line in native for line in equipped)
    foreign = sum(line not in native for line in equipped)
    if retained < SUBCLASSING_RULES.minimum_original_class_lines_retained:
        errors.append("subclassing must retain at least one native class skill line")
    if foreign > SUBCLASSING_RULES.maximum_foreign_class_lines_equipped:
        errors.append("subclassing cannot equip more than two foreign class skill lines")

    known = frozenset(line for lines in CLASS_SKILL_LINES.values() for line in lines)
    unknown = tuple(sorted(line for line in equipped if line not in known))
    if unknown:
        errors.append(f"unknown class skill line(s): {', '.join(unknown)}")
    return ClassRouteValidation(not errors, tuple(errors))


def validate_class_mastery_eligibility(
    *, native_class_line_ranks: tuple[int, int, int], subclassing: bool, selected_mastery_count: int
) -> ClassRouteValidation:
    errors: list[str] = []
    if subclassing:
        errors.append("Class Mastery cannot be used while subclassing")
    if len(native_class_line_ranks) != 3 or any(
        int(rank) < CLASS_MASTERY_RULES.requires_all_three_native_class_lines_rank
        for rank in native_class_line_ranks
    ):
        errors.append("Class Mastery requires all three native class skill lines at rank 50")
    count = int(selected_mastery_count)
    if count < 0:
        errors.append("selected_mastery_count cannot be negative")
    if count > CLASS_MASTERY_RULES.selectable_passives:
        errors.append("a character may select at most two Class Mastery passives")
    return ClassRouteValidation(not errors, tuple(errors))


def clamp_crux(value: int) -> int:
    return min(max(0, int(value)), CRUX_RULES.maximum_stacks)


def crux_can_generate(*, in_combat: bool, current_crux: int) -> bool:
    return bool(in_combat) and clamp_crux(current_crux) < CRUX_RULES.maximum_stacks


def ultimate_regen_from_standard_trigger(seconds: float) -> float:
    """Base hidden Ultimate gain only; excludes Heroism, sets, skills, and passives."""
    duration = min(max(0.0, float(seconds)), ULTIMATE_RULES.standard_regen_buff_seconds)
    return duration * ULTIMATE_RULES.standard_regen_per_second
