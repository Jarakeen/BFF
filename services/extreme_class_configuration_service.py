from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product

from minmax.character_build.character_class import CLASS_SKILL_LINES, CharacterClass
from minmax.character_build.class_configuration import ClassSkillLineConfiguration


@dataclass(frozen=True)
class ExtremeClassConfigurationCandidate:
    base_class: CharacterClass
    equipped_skill_lines: tuple[str, ...]
    is_pure_class: bool
    class_mastery_available: bool

    @property
    def foreign_skill_lines(self) -> tuple[str, ...]:
        native = CLASS_SKILL_LINES[self.base_class]
        return tuple(line for line in self.equipped_skill_lines if line not in native)


class ExtremeClassConfigurationService:
    """Enumerate every legal class-line configuration for the Extreme Build Lab.

    This service owns legality only. It deliberately does not invent a score for
    subclass lines or Class Mastery passives. Objective-specific scoring belongs
    in later effect-resolution layers once the corresponding passive effects are
    canonical and machine-readable.
    """

    @staticmethod
    def candidates_for_base_class(
        base_class: CharacterClass,
    ) -> tuple[ExtremeClassConfigurationCandidate, ...]:
        native_lines = tuple(sorted(CLASS_SKILL_LINES[base_class]))
        rows: list[ExtremeClassConfigurationCandidate] = []

        pure = ClassSkillLineConfiguration(equipped_skill_lines=native_lines)
        violations = pure.validate(base_class)
        if violations:
            raise ValueError("Invalid canonical pure-class configuration: " + "; ".join(violations))
        rows.append(
            ExtremeClassConfigurationCandidate(
                base_class=base_class,
                equipped_skill_lines=native_lines,
                is_pure_class=True,
                class_mastery_available=True,
            )
        )

        foreign_by_class = {
            character_class: tuple(sorted(lines))
            for character_class, lines in CLASS_SKILL_LINES.items()
            if character_class is not base_class
        }
        foreign_classes = tuple(sorted(foreign_by_class, key=lambda item: item.value))

        # Replace one native line with one line from one foreign class.
        for retained_native in combinations(native_lines, 2):
            for foreign_class in foreign_classes:
                for foreign_line in foreign_by_class[foreign_class]:
                    equipped = tuple(sorted((*retained_native, foreign_line)))
                    config = ClassSkillLineConfiguration(equipped_skill_lines=equipped)
                    if config.validate(base_class):
                        continue
                    rows.append(
                        ExtremeClassConfigurationCandidate(
                            base_class=base_class,
                            equipped_skill_lines=equipped,
                            is_pure_class=False,
                            class_mastery_available=False,
                        )
                    )

        # Replace two native lines. ESO permits only one line from any one
        # foreign class, so the two borrowed lines must come from two different
        # foreign classes.
        for retained_native in native_lines:
            for first_class, second_class in combinations(foreign_classes, 2):
                for first_line, second_line in product(
                    foreign_by_class[first_class],
                    foreign_by_class[second_class],
                ):
                    equipped = tuple(sorted((retained_native, first_line, second_line)))
                    config = ClassSkillLineConfiguration(equipped_skill_lines=equipped)
                    if config.validate(base_class):
                        continue
                    rows.append(
                        ExtremeClassConfigurationCandidate(
                            base_class=base_class,
                            equipped_skill_lines=equipped,
                            is_pure_class=False,
                            class_mastery_available=False,
                        )
                    )

        unique: dict[tuple[str, ...], ExtremeClassConfigurationCandidate] = {}
        for row in rows:
            unique[row.equipped_skill_lines] = row
        return tuple(
            unique[key]
            for key in sorted(unique)
        )

    @classmethod
    def all_candidates(cls) -> tuple[ExtremeClassConfigurationCandidate, ...]:
        rows: list[ExtremeClassConfigurationCandidate] = []
        for base_class in sorted(CharacterClass, key=lambda item: item.value):
            rows.extend(cls.candidates_for_base_class(base_class))
        return tuple(rows)

    @staticmethod
    def objective_checklist() -> tuple[str, ...]:
        return (
            "race passives",
            "pure class versus subclass configuration",
            "Class Mastery passives for pure-class candidates",
            "active-bar class and guild passives",
            "attribute allocation",
            "Mundus",
            "food/drink",
            "objective-specific potion snapshot",
            "legal gear-slot package by piece-count contribution",
            "maximum one Mythic",
            "monster-set and one-piece bonuses",
            "arena weapons",
            "armor, jewelry, and weapon traits",
            "armor, jewelry, and weapon enchantments",
        )
