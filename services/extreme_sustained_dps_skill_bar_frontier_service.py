from __future__ import annotations

"""Lazy legal two-bar skill-family/morph frontier for sustained-DPS generation.

Normal slot order is mechanically irrelevant to ESO build state, so this frontier
uses a canonical family order instead of multiplying the denominator by permutations.
Empty normal slots and an empty Ultimate slot remain legal. At most one member of a
base/morph family may appear on one bar; the same family may legally appear on both
bars.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re

from models.build_model import BAR_SKILL_COUNT, PlayerBuild
from services.skill_bar_eligibility import (
    CLASS_SKILL_LINES,
    NON_COMBAT_SKILL_LINES,
    SHARED_COMBAT_SKILL_LINES,
    VAMPIRE_SKILL_LINE,
    WEREWOLF_SKILL_LINE,
    is_eligible,
    is_player_active,
    is_ultimate,
)
from services.skill_choice_service import load_skill_choices


def _text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value: object) -> str:
    return _text(value).casefold()


def _line_key(value: object) -> str:
    return " ".join(
        part
        for part in re.split(r"[^a-z0-9]+", str(value or "").strip().casefold())
        if part
    )


@dataclass(frozen=True)
class ExtremeSustainedDPSSkillAlternative:
    ability_id: int
    base_ability_id: int
    name: str
    skill_line: str
    morph: int
    ultimate: bool


@dataclass(frozen=True)
class ExtremeSustainedDPSSkillFamily:
    base_ability_id: int
    skill_line: str
    ultimate: bool
    alternatives: tuple[ExtremeSustainedDPSSkillAlternative, ...]


@dataclass(frozen=True)
class ExtremeSustainedDPSSkillBarLegalityContext:
    character_class: str
    class_skill_lines: tuple[str, ...] = ()
    owned_skill_lines: tuple[str, ...] = ()
    weapon_skill_lines: tuple[str, ...] = ()
    armor_skill_lines: tuple[str, ...] = ()
    vampire: bool = False
    werewolf: bool = False
    transformed_form: str | None = None
    allowed_scribed_ability_ids: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if self.vampire and self.werewolf:
            raise ValueError("generated skill-bar context cannot be both Vampire and Werewolf")


@dataclass(frozen=True)
class ExtremeSustainedDPSSkillBarState:
    normal_skills: tuple[ExtremeSustainedDPSSkillAlternative, ...]
    ultimate_skill: ExtremeSustainedDPSSkillAlternative | None

    @property
    def names(self) -> tuple[str, ...]:
        values = [skill.name for skill in self.normal_skills]
        values += [""] * (BAR_SKILL_COUNT - len(values))
        values.append(self.ultimate_skill.name if self.ultimate_skill is not None else "")
        return tuple(values)


@dataclass(frozen=True)
class ExtremeSustainedDPSTwoBarSkillCandidate:
    structural_index: int
    front: ExtremeSustainedDPSSkillBarState
    back: ExtremeSustainedDPSSkillBarState
    build: PlayerBuild


@dataclass(frozen=True)
class ExtremeSustainedDPSSkillBarFrontier:
    front_candidate_count: int
    back_candidate_count: int
    candidate_count: int
    one_bar_only: bool
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class _BarIndexer:
    def __init__(
        self,
        *,
        normal_families: tuple[ExtremeSustainedDPSSkillFamily, ...],
        ultimate_families: tuple[ExtremeSustainedDPSSkillFamily, ...],
    ) -> None:
        self.normal_families = normal_families
        self.ultimate_families = ultimate_families
        self._normal_counts = tuple(len(row.alternatives) for row in normal_families)

    @lru_cache(maxsize=None)
    def _ways(self, start: int, choose: int) -> int:
        if choose == 0:
            return 1
        remaining = len(self.normal_families) - start
        if choose < 0 or remaining < choose:
            return 0
        skip = self._ways(start + 1, choose)
        take = self._normal_counts[start] * self._ways(start + 1, choose - 1)
        return skip + take

    @property
    def normal_candidate_count(self) -> int:
        return sum(
            self._ways(0, choose)
            for choose in range(0, min(BAR_SKILL_COUNT, len(self.normal_families)) + 1)
        )

    @property
    def ultimate_candidate_count(self) -> int:
        return 1 + sum(len(row.alternatives) for row in self.ultimate_families)

    @property
    def candidate_count(self) -> int:
        return self.normal_candidate_count * self.ultimate_candidate_count

    def _normal_at(self, index: int) -> tuple[ExtremeSustainedDPSSkillAlternative, ...]:
        target = int(index)
        total = self.normal_candidate_count
        if target < 0 or target >= total:
            raise IndexError("normal skill-bar state index out of range")

        chosen_count = 0
        for choose in range(0, min(BAR_SKILL_COUNT, len(self.normal_families)) + 1):
            bucket = self._ways(0, choose)
            if target < bucket:
                chosen_count = choose
                break
            target -= bucket

        selected: list[ExtremeSustainedDPSSkillAlternative] = []
        start = 0
        remaining_choose = chosen_count
        while remaining_choose > 0:
            family = self.normal_families[start]
            skip = self._ways(start + 1, remaining_choose)
            if target < skip:
                start += 1
                continue

            target -= skip
            tail = self._ways(start + 1, remaining_choose - 1)
            alternative_index = target // tail
            target %= tail
            selected.append(family.alternatives[alternative_index])
            remaining_choose -= 1
            start += 1

        return tuple(selected)

    def _ultimate_at(self, index: int) -> ExtremeSustainedDPSSkillAlternative | None:
        target = int(index)
        if target < 0 or target >= self.ultimate_candidate_count:
            raise IndexError("Ultimate skill-bar state index out of range")
        if target == 0:
            return None
        target -= 1
        for family in self.ultimate_families:
            if target < len(family.alternatives):
                return family.alternatives[target]
            target -= len(family.alternatives)
        raise IndexError("Ultimate skill-bar state index out of range")

    def state_at(self, index: int) -> ExtremeSustainedDPSSkillBarState:
        target = int(index)
        if target < 0 or target >= self.candidate_count:
            raise IndexError("skill-bar state index out of range")
        ultimate_count = self.ultimate_candidate_count
        normal_index = target // ultimate_count
        ultimate_index = target % ultimate_count
        return ExtremeSustainedDPSSkillBarState(
            normal_skills=self._normal_at(normal_index),
            ultimate_skill=self._ultimate_at(ultimate_index),
        )


class ExtremeSustainedDPSSkillBarFrontierService:
    """Preserve all legal base/morph alternatives without choosing a DPS winner."""

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        skill_rows: tuple[dict, ...] | None = None,
    ) -> None:
        if database_path is None and skill_rows is None:
            raise ValueError("database_path or skill_rows is required")
        self.database_path = Path(database_path) if database_path is not None else None
        self.skill_rows = (
            tuple(skill_rows)
            if skill_rows is not None
            else tuple(load_skill_choices(self.database_path))  # type: ignore[arg-type]
        )

    @staticmethod
    def _shared_line_owned(
        line: str,
        context: ExtremeSustainedDPSSkillBarLegalityContext,
    ) -> bool:
        line_id = _line_key(line)
        explicitly_owned = {_line_key(value) for value in context.owned_skill_lines}
        weapon_lines = {_line_key(value) for value in context.weapon_skill_lines}
        armor_lines = {_line_key(value) for value in context.armor_skill_lines}

        if line_id in weapon_lines or line_id in armor_lines:
            return True
        if line_id in {VAMPIRE_SKILL_LINE, WEREWOLF_SKILL_LINE}:
            return (
                (line_id == VAMPIRE_SKILL_LINE and context.vampire)
                or (line_id == WEREWOLF_SKILL_LINE and context.werewolf)
            )
        return line_id in explicitly_owned

    @classmethod
    def _row_allowed(
        cls,
        row: dict,
        context: ExtremeSustainedDPSSkillBarLegalityContext,
        *,
        slot_index: int,
    ) -> bool:
        if not is_player_active(row):
            return False

        ultimate = is_ultimate(row)
        if slot_index == BAR_SKILL_COUNT and not ultimate:
            return False
        if slot_index < BAR_SKILL_COUNT and ultimate:
            return False

        owner = _key(row.get("class_type"))
        line = _line_key(row.get("skill_line"))
        if owner:
            explicit_class_lines = {
                _line_key(value)
                for value in context.class_skill_lines
                if _line_key(value)
            }
            if not explicit_class_lines:
                selected_class = _key(context.character_class)
                explicit_class_lines = {
                    _line_key(value)
                    for value in CLASS_SKILL_LINES.get(selected_class, frozenset())
                }
            return line in explicit_class_lines

        if not is_eligible(
            row,
            character_class=context.character_class,
            slot_index=slot_index,
            vampire=context.vampire,
            werewolf=context.werewolf,
            transformed_form=context.transformed_form,
        ):
            return False

        if int(row.get("is_crafted") or 0):
            allowed = {int(value) for value in context.allowed_scribed_ability_ids}
            if int(row.get("ability_id") or 0) not in allowed:
                return False

        line = _line_key(row.get("skill_line"))
        if line in NON_COMBAT_SKILL_LINES:
            return False
        if line in SHARED_COMBAT_SKILL_LINES or line in {
            VAMPIRE_SKILL_LINE,
            WEREWOLF_SKILL_LINE,
        }:
            return cls._shared_line_owned(line, context)
        return False

    @classmethod
    def _families(
        cls,
        rows: tuple[dict, ...],
        context: ExtremeSustainedDPSSkillBarLegalityContext,
        *,
        ultimate: bool,
    ) -> tuple[ExtremeSustainedDPSSkillFamily, ...]:
        slot_index = BAR_SKILL_COUNT if ultimate else 0
        grouped: dict[int, dict[tuple[int, int], ExtremeSustainedDPSSkillAlternative]] = {}

        for row in rows:
            if is_ultimate(row) is not ultimate:
                continue
            if not cls._row_allowed(row, context, slot_index=slot_index):
                continue

            ability_id = int(row.get("ability_id") or 0)
            base_id = int(row.get("base_ability_id") or ability_id or 0)
            if ability_id <= 0 or base_id <= 0:
                continue
            name = _text(row.get("name"))
            if not name:
                continue
            morph = int(row.get("morph") or 0)
            alternative = ExtremeSustainedDPSSkillAlternative(
                ability_id=ability_id,
                base_ability_id=base_id,
                name=name,
                skill_line=_text(row.get("skill_line")),
                morph=morph,
                ultimate=ultimate,
            )
            key = (morph, ability_id)
            grouped.setdefault(base_id, {})[key] = alternative

        families = [
            ExtremeSustainedDPSSkillFamily(
                base_ability_id=base_id,
                skill_line=min(
                    (row.skill_line for row in alternatives.values()),
                    key=str.casefold,
                ),
                ultimate=ultimate,
                alternatives=tuple(
                    sorted(
                        alternatives.values(),
                        key=lambda row: (
                            row.morph,
                            row.name.casefold(),
                            row.ability_id,
                        ),
                    )
                ),
            )
            for base_id, alternatives in grouped.items()
        ]
        return tuple(
            sorted(
                families,
                key=lambda row: (
                    row.skill_line.casefold(),
                    row.base_ability_id,
                ),
            )
        )

    def _indexer(
        self,
        context: ExtremeSustainedDPSSkillBarLegalityContext,
    ) -> _BarIndexer:
        return _BarIndexer(
            normal_families=self._families(self.skill_rows, context, ultimate=False),
            ultimate_families=self._families(self.skill_rows, context, ultimate=True),
        )

    def frontier(
        self,
        *,
        front_context: ExtremeSustainedDPSSkillBarLegalityContext,
        back_context: ExtremeSustainedDPSSkillBarLegalityContext,
        one_bar_only: bool = False,
    ) -> ExtremeSustainedDPSSkillBarFrontier:
        front = self._indexer(front_context)
        back = self._indexer(back_context)
        unresolved: list[str] = []

        if front.candidate_count <= 0:
            unresolved.append("Front skill-bar legal denominator is empty")
        if not one_bar_only and back.candidate_count <= 0:
            unresolved.append("Back skill-bar legal denominator is empty")

        front_count = front.candidate_count
        back_count = 1 if one_bar_only else back.candidate_count
        total = front_count * back_count
        final_unresolved = tuple(dict.fromkeys(unresolved))

        return ExtremeSustainedDPSSkillBarFrontier(
            front_candidate_count=front_count,
            back_candidate_count=back_count,
            candidate_count=total,
            one_bar_only=bool(one_bar_only),
            denominator_proven=bool(total > 0 and not final_unresolved),
            evidence=(
                f"Front legal bar states: {front_count}",
                f"Back legal bar states: {back_count}",
                f"Two-bar skill denominator: {total}",
                "Empty normal slots and empty Ultimate slots remain legal states",
                "Normal-slot permutations are proof-safely collapsed to canonical family order",
                "One base/morph family may appear at most once per bar; front/back duplication remains legal",
                "Class skills follow the explicit generated class-route lines, including legal subclass lines",
                "Shared combat skill lines require explicit ownership or matching equipped weapon/armor evidence",
            ),
            unresolved=final_unresolved,
        )

    def candidate_at(
        self,
        baseline_build: PlayerBuild,
        *,
        front_context: ExtremeSustainedDPSSkillBarLegalityContext,
        back_context: ExtremeSustainedDPSSkillBarLegalityContext,
        index: int,
        one_bar_only: bool = False,
    ) -> ExtremeSustainedDPSTwoBarSkillCandidate:
        frontier = self.frontier(
            front_context=front_context,
            back_context=back_context,
            one_bar_only=one_bar_only,
        )
        if not frontier.denominator_proven:
            raise ValueError(
                "skill-bar frontier denominator is unresolved: "
                + "; ".join(frontier.unresolved)
            )
        target = int(index)
        if target < 0 or target >= frontier.candidate_count:
            raise IndexError("two-bar skill candidate index out of range")

        front_indexer = self._indexer(front_context)
        back_indexer = self._indexer(back_context)
        back_count = 1 if one_bar_only else back_indexer.candidate_count
        front_index = target // back_count
        back_index = target % back_count

        front = front_indexer.state_at(front_index)
        back = (
            ExtremeSustainedDPSSkillBarState((), None)
            if one_bar_only
            else back_indexer.state_at(back_index)
        )
        build = PlayerBuild.from_dict(baseline_build.to_dict())
        build.FrontBarSkills = list(front.names)
        build.BackBarSkills = list(back.names)

        return ExtremeSustainedDPSTwoBarSkillCandidate(
            structural_index=target,
            front=front,
            back=back,
            build=build,
        )

    def page(
        self,
        baseline_build: PlayerBuild,
        *,
        front_context: ExtremeSustainedDPSSkillBarLegalityContext,
        back_context: ExtremeSustainedDPSSkillBarLegalityContext,
        offset: int = 0,
        limit: int = 100,
        one_bar_only: bool = False,
    ) -> tuple[ExtremeSustainedDPSTwoBarSkillCandidate, ...]:
        frontier = self.frontier(
            front_context=front_context,
            back_context=back_context,
            one_bar_only=one_bar_only,
        )
        start = max(0, int(offset))
        size = max(0, int(limit))
        if size == 0 or start >= frontier.candidate_count:
            return ()
        return tuple(
            self.candidate_at(
                baseline_build,
                front_context=front_context,
                back_context=back_context,
                index=index,
                one_bar_only=one_bar_only,
            )
            for index in range(start, min(frontier.candidate_count, start + size))
        )


__all__ = [
    "ExtremeSustainedDPSSkillAlternative",
    "ExtremeSustainedDPSSkillBarFrontier",
    "ExtremeSustainedDPSSkillBarFrontierService",
    "ExtremeSustainedDPSSkillBarLegalityContext",
    "ExtremeSustainedDPSSkillBarState",
    "ExtremeSustainedDPSSkillFamily",
    "ExtremeSustainedDPSTwoBarSkillCandidate",
]
