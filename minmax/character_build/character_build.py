from __future__ import annotations

from dataclasses import dataclass, field

from ..role import Role
from .bar import Bar
from .champion_points import ChampionPointAllocation
from .character_class import CLASS_SKILL_LINES, CharacterClass, class_owns_skill_line
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
    """
    Raised when something attempts to resolve effects for a CharacterBuild
    that fails `validate()`. Effect resolution must respect the character's
    actual build constraints, so it must never silently resolve effects
    for a build ESO itself would not allow.
    """

    def __init__(self, violations: tuple[str, ...]):
        self.violations = violations
        super().__init__(
            "CharacterBuild is not mechanically legal: " + "; ".join(violations)
        )


@dataclass(frozen=True)
class CharacterBuild:
    """
    The mechanical representation of one real ESO character build: enough
    to determine exactly what effects are actually available to it at a
    specific moment (see effect_availability.py), and enough to validate
    the hard constraints ESO itself enforces.

    This is deliberately separate from the legacy `minmax.build.Build`
    (used by the flat StatEngine pipeline) - that type is untouched by
    this module. CharacterBuild models the full mechanical shape of a
    build (bars, slots, weapon-line access, passive dependency); it does
    not compute final stat totals itself.
    """

    name: str
    character_class: CharacterClass
    role: Role
    race_id: int | None = None

    mythic: ArmorPiece | None = None
    armor: tuple[ArmorPiece, ...] = field(default_factory=tuple)
    champion_points: tuple[ChampionPointAllocation, ...] = field(default_factory=tuple)

    front_bar: Bar | None = None
    back_bar: Bar | None = None

    def bars(self) -> tuple[Bar, ...]:
        return tuple(bar for bar in (self.front_bar, self.back_bar) if bar is not None)

    def all_armor_pieces(self) -> tuple[ArmorPiece, ...]:
        """Every equipped non-weapon piece, including the mythic if present."""
        if self.mythic is None:
            return self.armor
        return self.armor + (self.mythic,)

    def validate(self) -> tuple[str, ...]:
        """
        Return every hard-constraint violation found in this build. An
        empty tuple means the build is mechanically legal. This never
        raises - callers decide what to do with violations (reject,
        warn, or simply report them).
        """
        problems: list[str] = []

        problems.extend(self._mythic_violations())
        problems.extend(self._bar_violations())
        problems.extend(self._class_ownership_violations())
        problems.extend(self._weapon_skill_line_violations())

        return tuple(problems)

    def is_valid(self) -> bool:
        return len(self.validate()) == 0

    # -- individual constraint checks -------------------------------------

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

    def _bar_violations(self) -> tuple[str, ...]:
        problems: list[str] = []
        for bar in self.bars():
            problems.extend(bar.violations())
        return tuple(problems)

    def _class_ownership_violations(self) -> tuple[str, ...]:
        """A pure class cannot arbitrarily select another class's passives."""
        problems: list[str] = []
        for bar in self.bars():
            for slot in bar.slots:
                owning_class = _skill_line_owning_class(slot.skill_line_id)
                if owning_class is None:
                    continue  # Not a class line at all (weapon/guild/world/racial).

                if not class_owns_skill_line(
                    self.character_class, slot.skill_line_id
                ):
                    problems.append(
                        f"{bar.bar_id.value} bar slots skill "
                        f"'{slot.skill_id}' from '{slot.skill_line_id}', which "
                        f"belongs to {owning_class.value}, not "
                        f"{self.character_class.value}."
                    )
        return tuple(problems)

    def _weapon_skill_line_violations(self) -> tuple[str, ...]:
        """
        A slotted skill whose skill_line_id names a *weapon* skill line
        must match the weapon skill line that bar's equipped weapon(s)
        actually make available.
        """
        problems: list[str] = []
        for bar in self.bars():
            try:
                available_line = bar.weapon_skill_line
            except ValueError:
                continue  # Already reported by bar.violations().

            for slot in bar.slots:
                if slot.skill_line_id not in _WEAPON_SKILL_LINE_IDS:
                    continue

                if slot.skill_line_id != available_line.value:
                    problems.append(
                        f"{bar.bar_id.value} bar slots skill "
                        f"'{slot.skill_id}' from weapon skill line "
                        f"'{slot.skill_line_id}', but this bar's equipped "
                        f"weapon(s) only make "
                        f"'{available_line.value}' available."
                    )
        return tuple(problems)
