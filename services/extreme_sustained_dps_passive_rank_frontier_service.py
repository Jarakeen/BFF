from __future__ import annotations

"""Lazy passive-rank frontier for one explicit generated progression ownership state.

This service does not invent skill-line ownership. It varies ranks only for passives
belonging to the candidate class's native class lines or lines already present in the
supplied CharacterProgression. Race passives remain owned by race progression.
"""

from dataclasses import dataclass, replace

from minmax.character_build.character_class import CLASS_SKILL_LINES, CharacterClass
from minmax.character_progression import CharacterProgression
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
    ExtremeSkillUniverseService,
)


def _line_key(value: object) -> str:
    return "_".join(
        str(value or "").strip().casefold().replace("-", " ").replace("_", " ").split()
    )


def _class_key(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


@dataclass(frozen=True)
class ExtremeSustainedDPSPassiveRankAxis:
    passive_name: str
    skill_line: str
    max_rank: int
    rank_choices: tuple[int, ...]

    @property
    def choice_count(self) -> int:
        return len(self.rank_choices)


@dataclass(frozen=True)
class ExtremeSustainedDPSPassiveRankCandidate:
    structural_index: int
    selected_ranks: tuple[tuple[str, int], ...]
    progression: CharacterProgression


@dataclass(frozen=True)
class ExtremeSustainedDPSPassiveRankFrontier:
    axes: tuple[ExtremeSustainedDPSPassiveRankAxis, ...]
    candidate_count: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.axes, tuple):
            raise TypeError("passive-rank frontier axes must be a tuple")
        if isinstance(self.candidate_count, bool) or not isinstance(self.candidate_count, int):
            raise TypeError("passive-rank frontier candidate_count must be an integer")
        if self.candidate_count < 0:
            raise ValueError("passive-rank frontier candidate_count cannot be negative")
        if not isinstance(self.denominator_proven, bool):
            raise TypeError("passive-rank frontier denominator_proven must be boolean")
        if not isinstance(self.evidence, tuple):
            raise TypeError("passive-rank frontier evidence must be a tuple")
        if not isinstance(self.unresolved, tuple):
            raise TypeError("passive-rank frontier unresolved must be a tuple")


class ExtremeSustainedDPSPassiveRankFrontierService:
    """Index legal rank states for explicitly owned combat-line passives lazily."""

    def __init__(self, universe_service: ExtremeSkillUniverseService | object) -> None:
        self.universe_service = universe_service

    @classmethod
    def from_database(cls, database_path) -> "ExtremeSustainedDPSPassiveRankFrontierService":
        return cls(ExtremeSkillUniverseService(database_path))

    @staticmethod
    def _class_lines(character_class: str) -> frozenset[str]:
        key = _class_key(character_class)
        try:
            cls = CharacterClass(key)
        except ValueError:
            return frozenset()
        return frozenset(_line_key(value) for value in CLASS_SKILL_LINES.get(cls, frozenset()))

    def frontier(
        self,
        progression: CharacterProgression,
        *,
        character_class: str,
    ) -> ExtremeSustainedDPSPassiveRankFrontier:
        owned = {_line_key(value) for value in progression.owned_skill_lines if _line_key(value)}
        class_lines = self._class_lines(character_class)
        if str(character_class or "").strip() and not class_lines:
            unresolved = (f"Unsupported candidate class for passive-rank frontier: {character_class}",)
            return ExtremeSustainedDPSPassiveRankFrontier(
                axes=(),
                candidate_count=0,
                denominator_proven=False,
                evidence=(),
                unresolved=unresolved,
            )

        allowed_lines = owned | set(class_lines)
        axes: list[ExtremeSustainedDPSPassiveRankAxis] = []
        unresolved: list[str] = []
        seen: set[str] = set()

        for row in self.universe_service.passives():
            if not isinstance(row, ExtremePlayerSkillRecord):
                # Test doubles and compatible records are allowed; this is only a
                # structural service, so duck-typed fields remain sufficient.
                pass
            if getattr(row, "domain", None) is ExtremeSkillDomain.RACIAL:
                continue
            line = _line_key(getattr(row, "skill_line", ""))
            if not line or line not in allowed_lines:
                continue
            if not bool(getattr(row, "combat_line", True)):
                continue

            name = " ".join(str(getattr(row, "name", "") or "").strip().split())
            key = name.casefold()
            if not name:
                unresolved.append(f"{getattr(row, 'skill_line', '')}: passive has no canonical name")
                continue
            if key in seen:
                unresolved.append(f"Duplicate canonical passive identity in owned lines: {name}")
                continue
            seen.add(key)

            max_rank = getattr(row, "max_rank", None)
            try:
                rank = int(max_rank)
            except (TypeError, ValueError):
                rank = 0
            if rank <= 0:
                unresolved.append(f"{name}: canonical passive max rank is unavailable")
                continue

            axes.append(
                ExtremeSustainedDPSPassiveRankAxis(
                    passive_name=name,
                    skill_line=str(getattr(row, "skill_line", "") or "").strip(),
                    max_rank=rank,
                    rank_choices=tuple(range(rank + 1)),
                )
            )

        axes.sort(key=lambda row: (row.skill_line.casefold(), row.passive_name.casefold()))
        count = 1
        for axis in axes:
            count *= axis.choice_count

        if not axes and not unresolved:
            unresolved.append("No owned combat-line passive ranks are available for generated search")

        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        return ExtremeSustainedDPSPassiveRankFrontier(
            axes=tuple(axes),
            candidate_count=count if axes else 0,
            denominator_proven=bool(axes and count > 0 and not final_unresolved),
            evidence=(
                f"Explicitly owned non-class skill lines: {len(owned)}",
                f"Native candidate class lines: {len(class_lines)}",
                f"Passive rank axes: {len(axes)}",
                f"Lazy passive-rank denominator: {count if axes else 0}",
                "Ranks include 0 through canonical max rank; skill-line ownership is never invented",
                "Racial passive progression remains a separate race-owned axis",
            ),
            unresolved=final_unresolved,
        )

    def candidate_at(
        self,
        progression: CharacterProgression,
        *,
        character_class: str,
        index: int,
    ) -> ExtremeSustainedDPSPassiveRankCandidate:
        frontier = self.frontier(progression, character_class=character_class)
        if not frontier.denominator_proven:
            raise ValueError(
                "passive-rank frontier denominator is unresolved: "
                + "; ".join(frontier.unresolved)
            )

        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("passive-rank candidate index must be an integer")
        target = index
        if target < 0 or target >= frontier.candidate_count:
            raise IndexError("passive-rank candidate index out of range")

        remainder = target
        selected_reversed: list[tuple[str, int]] = []
        for axis in reversed(frontier.axes):
            local = remainder % axis.choice_count
            remainder //= axis.choice_count
            selected_reversed.append((axis.passive_name, axis.rank_choices[local]))

        selected = tuple(reversed(selected_reversed))
        ranks = dict(progression.passive_ranks or {})
        for name, rank in selected:
            ranks[name] = int(rank)

        owned_lines = tuple(
            dict.fromkeys(
                (
                    *progression.owned_skill_lines,
                    *(axis.skill_line for axis in frontier.axes),
                )
            )
        )
        candidate = replace(
            progression,
            owned_skill_lines=owned_lines,
            passive_ranks=ranks,
        )
        return ExtremeSustainedDPSPassiveRankCandidate(
            structural_index=target,
            selected_ranks=selected,
            progression=candidate,
        )

    def page(
        self,
        progression: CharacterProgression,
        *,
        character_class: str,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[ExtremeSustainedDPSPassiveRankCandidate, ...]:
        frontier = self.frontier(progression, character_class=character_class)
        start = max(0, int(offset))
        size = max(0, int(limit))
        if size == 0 or start >= frontier.candidate_count:
            return ()
        return tuple(
            self.candidate_at(
                progression,
                character_class=character_class,
                index=index,
            )
            for index in range(start, min(frontier.candidate_count, start + size))
        )


__all__ = [
    "ExtremeSustainedDPSPassiveRankAxis",
    "ExtremeSustainedDPSPassiveRankCandidate",
    "ExtremeSustainedDPSPassiveRankFrontier",
    "ExtremeSustainedDPSPassiveRankFrontierService",
]
