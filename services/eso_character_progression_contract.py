from __future__ import annotations

"""Source-backed ESO base character/progression contract.

This module is intentionally narrower than combat math. It describes the rules
that determine what a legal player character can own, level, slot, morph, and
combine before downstream systems score damage, healing, tanking, sustain, or
Extreme Build objectives.

Design rules:
- Treat these as legality/progression constraints, not as skill-effect truth.
- Keep base character rules separate from gear/set/passive effect projection.
- Never infer an unlocked skill/passive from its name alone; callers should join
  these rules to canonical skill-line/rank data from ``eso.db``.
- Subclassing and Class Mastery are mutually exclusive character routes.
- Runtime resources such as Ultimate and Crux remain runtime state, not static
  character-sheet bonuses.

Source snapshot provenance (uploaded reference pages reviewed 2026-09-07):
- UESP Online:Attributes, revision 2861719
- UESP Online:Health, revision 2861707
- UESP Online:Magicka, revision 2861709
- UESP Online:Stamina, revision 3044713
- UESP Online:Skills, revision 3600114
- UESP Online:Ultimate, revision 3543403
- UESP Online:Crux, revision 3559618
- UESP Online:Class Mastery, revision 3581024
- ESO-Hub Subclassing guide, modified 2026-05-20

Values in this contract should be re-reviewed when an ESO update changes base
progression, subclassing, Class Mastery, or resource rules.
"""

from dataclasses import dataclass
from enum import Enum


class AttributeKey(str, Enum):
    HEALTH = "health"
    MAGICKA = "magicka"
    STAMINA = "stamina"


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
        if attribute_points < 0:
            raise ValueError("attribute_points cannot be negative")
        if attribute_points > CHARACTER_RULES.attribute_points_at_level_50:
            raise ValueError("attribute_points exceed the level-50 allocation ceiling")
        return (
            self.level_coefficient * int(level)
            + self.base_constant
            + self.per_attribute_point * int(attribute_points)
        )


BASE_ATTRIBUTES = {
    AttributeKey.HEALTH: BaseAttributeRule(
        key=AttributeKey.HEALTH,
        level_coefficient=300.0,
        base_constant=1000.0,
        per_attribute_point=122.0,
        level_50_unallocated=16000.0,
        level_50_all_64_points=23808.0,
    ),
    AttributeKey.MAGICKA: BaseAttributeRule(
        key=AttributeKey.MAGICKA,
        level_coefficient=220.0,
        base_constant=1000.0,
        per_attribute_point=111.0,
        level_50_unallocated=12000.0,
        level_50_all_64_points=19104.0,
    ),
    AttributeKey.STAMINA: BaseAttributeRule(
        key=AttributeKey.STAMINA,
        level_coefficient=220.0,
        base_constant=1000.0,
        per_attribute_point=111.0,
        level_50_unallocated=12000.0,
        level_50_all_64_points=19104.0,
    ),
}


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
class SkillProgressionRules:
    # Passive ranks are data-driven because individual passives vary.
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


@dataclass(frozen=True)
class UltimateRules:
    maximum_resource: int = 500
    one_ultimate_per_bar: bool = True
    normal_cast_consumes_accumulated_resource: bool = True
    light_attack_regen_buff_seconds: float = 9.0
    light_attack_regen_per_second: float = 3.0
    light_attack_regen_total: float = 27.0
    regen_trigger_light_or_heavy_attack: bool = True
    regen_trigger_heal_other: bool = True
    regen_trigger_self_heal: bool = False
    regen_trigger_block: bool = True
    regen_trigger_dodge: bool = True


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

CLASS_SKILL_LINES = {
    "dragonknight": frozenset({"ardent flame", "draconic power", "earthen heart"}),
    "sorcerer": frozenset({"dark magic", "daedric summoning", "storm calling"}),
    "nightblade": frozenset({"assassination", "shadow", "siphoning"}),
    "templar": frozenset({"aedric spear", "dawn's wrath", "restoring light"}),
    "warden": frozenset({"animal companions", "green balance", "winter's embrace"}),
    "necromancer": frozenset({"grave lord", "bone tyrant", "living death"}),
    "arcanist": frozenset({"herald of the tome", "soldier of apocrypha", "curative runeforms"}),
}


@dataclass(frozen=True)
class ClassRouteValidation:
    legal: bool
    errors: tuple[str, ...]


def _key(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def validate_character_level(level: int) -> None:
    if int(level) < CHARACTER_RULES.minimum_level:
        raise ValueError("character level must be at least 1")
    if int(level) > CHARACTER_RULES.normal_level_cap:
        raise ValueError(
            "this contract models normal character levels 1-50; Champion progression is separate"
        )


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


def validate_bar_shape(
    *,
    normal_skill_count: int,
    ultimate_count: int,
    character_level: int = 50,
) -> None:
    validate_character_level(character_level)
    if int(normal_skill_count) > CHARACTER_RULES.normal_skill_slots_per_bar:
        raise ValueError("a skill bar cannot contain more than five normal skills")
    if int(ultimate_count) > CHARACTER_RULES.ultimate_slots_per_bar:
        raise ValueError("a skill bar cannot contain more than one Ultimate")
    if int(normal_skill_count) < 0 or int(ultimate_count) < 0:
        raise ValueError("slot counts cannot be negative")


def available_bar_count(character_level: int) -> int:
    validate_character_level(character_level)
    return (
        CHARACTER_RULES.bars_after_weapon_swap
        if int(character_level) >= CHARACTER_RULES.weapon_swap_unlock_level
        else 1
    )


def validate_subclass_route(
    *,
    base_class: str,
    equipped_class_lines: tuple[str, ...],
) -> ClassRouteValidation:
    base = _key(base_class)
    native = CLASS_SKILL_LINES.get(base)
    errors: list[str] = []
    if native is None:
        errors.append(f"unknown base class: {base_class}")
        return ClassRouteValidation(False, tuple(errors))

    equipped = tuple(_key(line) for line in equipped_class_lines if _key(line))
    if len(equipped) != SUBCLASSING_RULES.total_equipped_class_lines:
        errors.append("a subclass route must equip exactly three class skill lines")
    if len(set(equipped)) != len(equipped):
        errors.append("equipped class skill lines must be distinct")

    retained = sum(1 for line in equipped if line in native)
    foreign = sum(1 for line in equipped if line not in native)
    if retained < SUBCLASSING_RULES.minimum_original_class_lines_retained:
        errors.append("subclassing must retain at least one native class skill line")
    if foreign > SUBCLASSING_RULES.maximum_foreign_class_lines_equipped:
        errors.append("subclassing cannot equip more than two foreign class skill lines")

    all_known_lines = frozenset(line for lines in CLASS_SKILL_LINES.values() for line in lines)
    unknown = tuple(sorted(line for line in equipped if line not in all_known_lines))
    if unknown:
        errors.append(f"unknown class skill line(s): {', '.join(unknown)}")

    return ClassRouteValidation(not errors, tuple(errors))


def validate_class_mastery_eligibility(
    *,
    native_class_line_ranks: tuple[int, int, int],
    subclassing: bool,
    selected_mastery_count: int,
) -> ClassRouteValidation:
    errors: list[str] = []
    if subclassing:
        errors.append("Class Mastery cannot be used while subclassing")
    if len(native_class_line_ranks) != 3 or any(
        int(rank) < CLASS_MASTERY_RULES.requires_all_three_native_class_lines_rank
        for rank in native_class_line_ranks
    ):
        errors.append("Class Mastery requires all three native class skill lines at rank 50")
    if int(selected_mastery_count) < 0:
        errors.append("selected_mastery_count cannot be negative")
    if int(selected_mastery_count) > CLASS_MASTERY_RULES.selectable_passives:
        errors.append("a character may select at most two Class Mastery passives")
    return ClassRouteValidation(not errors, tuple(errors))


def clamp_crux(value: int) -> int:
    return min(max(0, int(value)), CRUX_RULES.maximum_stacks)


def crux_can_generate(*, in_combat: bool, current_crux: int) -> bool:
    return bool(in_combat) and clamp_crux(current_crux) < CRUX_RULES.maximum_stacks


def ultimate_regen_from_standard_trigger(seconds: float) -> float:
    """Return base hidden Ultimate-regeneration gain for one standard trigger.

    This does not include skills, sets, passives, Heroism, or other additional
    Ultimate sources. The standard hidden regeneration window is capped at the
    documented 9-second duration.
    """
    duration = min(max(0.0, float(seconds)), ULTIMATE_RULES.light_attack_regen_buff_seconds)
    return duration * ULTIMATE_RULES.light_attack_regen_per_second
