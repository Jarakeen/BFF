from __future__ import annotations

from dataclasses import dataclass, field

from .character_class import CLASS_SKILL_LINES, CharacterClass

CLASS_SKILL_LINE_COUNT = 3
MAX_SUBCLASS_LINES = 2
MAX_CLASS_MASTERY_POINTS = 2


def _owning_class(skill_line_id: str) -> CharacterClass | None:
    for character_class, lines in CLASS_SKILL_LINES.items():
        if skill_line_id in lines:
            return character_class
    return None


@dataclass(frozen=True)
class ClassMasteryConfiguration:
    """The Class Mastery choices made by a pure-class build.

    The ESO database remains authoritative for which mastery abilities belong
    to each class. This object stores only the selected ability IDs.
    """

    passive_ability_ids: tuple[int, ...] = field(default_factory=tuple)

    def validate(self) -> tuple[str, ...]:
        problems: list[str] = []
        if len(self.passive_ability_ids) > MAX_CLASS_MASTERY_POINTS:
            problems.append(
                f"Class Mastery may select at most {MAX_CLASS_MASTERY_POINTS} "
                f"passives, found {len(self.passive_ability_ids)}."
            )
        if len(set(self.passive_ability_ids)) != len(self.passive_ability_ids):
            problems.append("Class Mastery passive selections must be unique.")
        if any(ability_id <= 0 for ability_id in self.passive_ability_ids):
            problems.append("Class Mastery ability IDs must be positive integers.")
        return tuple(problems)


@dataclass(frozen=True)
class ClassSkillLineConfiguration:
    """The three class skill lines equipped by one build.

    An empty selection means the character's three native lines. A non-empty
    selection must contain exactly three lines, retain at least one native
    line, replace no more than two lines, and use at most one foreign line
    from any single class.
    """

    equipped_skill_lines: tuple[str, ...] = field(default_factory=tuple)
    class_mastery: ClassMasteryConfiguration = field(
        default_factory=ClassMasteryConfiguration
    )

    def effective_skill_lines(
        self, character_class: CharacterClass
    ) -> tuple[str, ...]:
        if not self.equipped_skill_lines:
            return tuple(sorted(CLASS_SKILL_LINES[character_class]))
        return self.equipped_skill_lines

    def foreign_skill_lines(
        self, character_class: CharacterClass
    ) -> tuple[str, ...]:
        native = CLASS_SKILL_LINES[character_class]
        return tuple(
            line
            for line in self.effective_skill_lines(character_class)
            if line not in native and _owning_class(line) is not None
        )

    def is_pure_class(self, character_class: CharacterClass) -> bool:
        return set(self.effective_skill_lines(character_class)) == set(
            CLASS_SKILL_LINES[character_class]
        )

    def configuration_allows_class_mastery(
        self, character_class: CharacterClass
    ) -> bool:
        return self.is_pure_class(character_class)

    def class_mastery_available(
        self,
        character_class: CharacterClass,
        mastered_skill_lines: frozenset[str] | set[str] | tuple[str, ...],
    ) -> bool:
        """Whether progression plus the current build permit Class Mastery."""
        native = CLASS_SKILL_LINES[character_class]
        return self.is_pure_class(character_class) and native.issubset(
            set(mastered_skill_lines)
        )

    def validate(self, character_class: CharacterClass) -> tuple[str, ...]:
        problems: list[str] = []
        lines = self.effective_skill_lines(character_class)

        if len(lines) != CLASS_SKILL_LINE_COUNT:
            problems.append(
                f"A build must equip exactly {CLASS_SKILL_LINE_COUNT} class "
                f"skill lines, got {len(lines)}."
            )
        if len(set(lines)) != len(lines):
            problems.append("Equipped class skill lines must be unique.")

        native = CLASS_SKILL_LINES[character_class]
        foreign = self.foreign_skill_lines(character_class)

        if not set(lines) & native:
            problems.append("Subclassing must retain at least one native class skill line.")
        if len(foreign) > MAX_SUBCLASS_LINES:
            problems.append(
                f"Subclassing may replace at most {MAX_SUBCLASS_LINES} native "
                f"class skill lines, found {len(foreign)} foreign lines."
            )

        foreign_classes = [_owning_class(line) for line in foreign]
        foreign_classes = [value for value in foreign_classes if value is not None]
        if len(set(foreign_classes)) != len(foreign_classes):
            problems.append(
                "A subclass configuration may use at most one skill line from each foreign class."
            )

        unknown_lines = [line for line in lines if _owning_class(line) is None]
        if unknown_lines:
            problems.append(
                "Equipped class skill lines contain unknown class-line identities: "
                + ", ".join(unknown_lines)
            )

        if not self.configuration_allows_class_mastery(character_class) and self.class_mastery.passive_ability_ids:
            problems.append("Class Mastery passives cannot be selected while subclassing.")

        problems.extend(self.class_mastery.validate())
        return tuple(problems)
