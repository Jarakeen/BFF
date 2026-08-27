from __future__ import annotations

from dataclasses import dataclass, field

from ..role import Role
from .bar import Bar
from .champion_points import ChampionPointAllocation
from .character_class import CLASS_SKILL_LINES, CharacterClass
from .class_configuration import ClassMasteryConfiguration, ClassSkillLineConfiguration
from .gear_piece import ArmorPiece, GearPieceCategory
from .weapon_type import WeaponSkillLine


def _skill_line_owning_class(skill_line_id: str) -> CharacterClass | None:
    """Which class (if any) owns this skill-line identity as a class line?"""
    for character_class, lines in CLASS_SKILL_LINES.items():
        if skill_line_id in lines:
            return character_class
    return None


_WEAPON_SKILL_LINE_IDS = frozenset(line.value for line in WeaponSkillLine)


class IllegalBuildError(ValueError):
    """Raised when an illegal CharacterBuild reaches effect resolution."""

    def __init__(self, violations: tuple[str, ...]):
        self.violations = violations
        super().__init__(
            "CharacterBuild is not mechanically legal: " + "; ".join(violations)
        )


@dataclass(frozen=True)
class CharacterBuild:
    """Canonical mechanical configuration for one ESO character.

    The build stores selections, not calculated results. Character identity
    and progression are represented by `character_id`, `character_name`, and
    the progression snapshot used for Class Mastery eligibility. Evaluation
    services consume this object and produce calculated state separately.
    """

    name: str
    character_class: CharacterClass
    role: Role
    race_id: int | None = None

    character_id: str | None = None
    character_name: str | None = None
    mastered_class_skill_lines: frozenset[str] = field(default_factory=frozenset)

    # Persistent character state that affects build legality/effects.
    vampire: bool = False
    werewolf: bool = False

    # Persistent build configuration selections. IDs are canonical BFF/ESO
    # identities; repositories remain responsible for resolving their data.
    mundus_id: str | None = None
    food_id: str | None = None
    drink_id: str | None = None
    potion_id: str | None = None
    poison_id: str | None = None

    mythic: ArmorPiece | None = None
    armor: tuple[ArmorPiece, ...] = field(default_factory=tuple)
    champion_points: tuple[ChampionPointAllocation, ...] = field(default_factory=tuple)

    class_skill_lines: ClassSkillLineConfiguration = field(
        default_factory=ClassSkillLineConfiguration
    )

    front_bar: Bar | None = None
    back_bar: Bar | None = None

    def bars(self) -> tuple[Bar, ...]:
        return tuple(bar for bar in (self.front_bar, self.back_bar) if bar is not None)

    def all_armor_pieces(self) -> tuple[ArmorPiece, ...]:
        """Every equipped non-weapon piece, including the mythic if present."""
        if self.mythic is None:
            return self.armor
        return self.armor + (self.mythic,)

    @property
    def effective_class_skill_lines(self) -> tuple[str, ...]:
        return self.class_skill_lines.effective_skill_lines(self.character_class)

    @property
    def class_mastery(self) -> ClassMasteryConfiguration:
        return self.class_skill_lines.class_mastery

    @property
    def is_subclassed(self) -> bool:
        return not self.class_skill_lines.is_pure_class(self.character_class)

    @property
    def class_mastery_configuration_eligible(self) -> bool:
        return self.class_skill_lines.configuration_allows_class_mastery(
            self.character_class
        )

    @property
    def class_mastery_available(self) -> bool:
        return self.class_skill_lines.class_mastery_available(
            self.character_class,
            self.mastered_class_skill_lines,
        )

    def validate(self) -> tuple[str, ...]:
        """Return all known hard-constraint violations.

        Empty tuple means the current configuration is mechanically legal.
        An incomplete build is allowed while it is being constructed; this
        validator rejects contradictions rather than requiring every slot to
        be populated.
        """
        problems: list[str] = []

        if self.vampire and self.werewolf:
            problems.append("A character cannot be both Vampire and Werewolf.")

        problems.extend(self._mythic_violations())
        problems.extend(self._armor_slot_violations())
        problems.extend(self._bar_violations())
        problems.extend(self.class_skill_lines.validate(self.character_class))
        problems.extend(self._class_ownership_violations())
        problems.extend(self._weapon_skill_line_violations())
        problems.extend(self._class_mastery_progression_violations())

        return tuple(problems)

    def is_valid(self) -> bool:
        return len(self.validate()) == 0

    def _mythic_violations(self) -> tuple[str, ...]:
        mythic_pieces = [
            piece
            for piece in self.all_armor_pieces()
            if piece.category == GearPieceCategory.MYTHIC
        ]
        if len(mythic_pieces) > 1:
            return (
                f"A build may equip at most one mythic item, found "
                f"{len(mythic_pieces)}.",
            )
        return ()

    def _armor_slot_violations(self) -> tuple[str, ...]:
        seen: set[str] = set()
        problems: list[str] = []
        for piece in self.all_armor_pieces():
            slot = piece.slot.value
            if slot in seen:
                problems.append(f"Gear slot '{slot}' is equipped more than once.")
            seen.add(slot)
        return tuple(problems)

    def _bar_violations(self) -> tuple[str, ...]:
        problems: list[str] = []
        for bar in self.bars():
            problems.extend(bar.violations())
        return tuple(problems)

    def _class_ownership_violations(self) -> tuple[str, ...]:
        """Ensure slotted class skills belong to an equipped class line."""
        problems: list[str] = []
        allowed_lines = set(self.effective_class_skill_lines)

        for bar in self.bars():
            for slot in bar.slots:
                owning_class = _skill_line_owning_class(slot.skill_line_id)
                if owning_class is None:
                    continue

                if slot.skill_line_id not in allowed_lines:
                    problems.append(
                        f"{bar.bar_id.value} bar slots skill '{slot.skill_id}' from "
                        f"class skill line '{slot.skill_line_id}', but that line is "
                        f"not equipped by this build."
                    )
                    if owning_class != self.character_class:
                        problems.append(
                            f"{bar.bar_id.value} bar slots skill '{slot.skill_id}' from "
                            f"'{slot.skill_line_id}', which belongs to {owning_class.value}, "
                            f"not {self.character_class.value}."
                        )

        return tuple(problems)

    def _class_mastery_progression_violations(self) -> tuple[str, ...]:
        selected = self.class_mastery.passive_ability_ids
        if not selected:
            return ()
        if not self.class_mastery_available:
            return (
                "Class Mastery passives are selected, but the character has not "
                "mastered all three native class skill lines or the build is subclassed.",
            )
        return ()

    def _weapon_skill_line_violations(self) -> tuple[str, ...]:
        """Ensure weapon-line skills match the weapon equipped on that bar."""
        problems: list[str] = []
        for bar in self.bars():
            try:
                available_line = bar.weapon_skill_line
            except ValueError:
                continue

            for slot in bar.slots:
                if slot.skill_line_id not in _WEAPON_SKILL_LINE_IDS:
                    continue

                if slot.skill_line_id != available_line.value:
                    problems.append(
                        f"{bar.bar_id.value} bar slots skill "
                        f"'{slot.skill_id}' from weapon skill line "
                        f"'{slot.skill_line_id}', but this bar's equipped "
                        f"weapon(s) only make '{available_line.value}' available."
                    )
        return tuple(problems)
