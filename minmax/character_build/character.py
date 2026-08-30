from __future__ import annotations

from dataclasses import dataclass, field

from ..role import Role
from .character_class import CharacterClass


@dataclass(frozen=True)
class Character:
    """Canonical identity and progression record for one ESO character.

    A Character is not a build. It owns persistent identity/progression;
    CharacterBuild instances represent configurations of that character for
    parses, bosses, trials, or other contexts.
    """

    character_id: str
    name: str
    character_class: CharacterClass
    role: Role
    race_id: int | None = None
    mastered_class_skill_lines: frozenset[str] = field(default_factory=frozenset)
    vampire: bool = False
    werewolf: bool = False

    def validate(self) -> tuple[str, ...]:
        problems: list[str] = []
        if self.vampire and self.werewolf:
            problems.append("A character cannot be both Vampire and Werewolf.")
        return tuple(problems)

    def has_mastered_skill_line(self, skill_line_id: str) -> bool:
        return skill_line_id in self.mastered_class_skill_lines
