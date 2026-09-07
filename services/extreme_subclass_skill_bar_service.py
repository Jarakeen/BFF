from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path

from minmax.character_build.character_class import CLASS_SKILL_LINES
from services.extreme_skill_standing_effect_service import ExtremeSkillStandingEffectService
from services.skill_bar_eligibility import is_player_active, is_ultimate
from services.skill_choice_service import load_skill_choices


def _line_token(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


_CANONICAL_LINE_BY_TOKEN = {
    _line_token(line): line
    for lines in CLASS_SKILL_LINES.values()
    for line in lines
}


@dataclass(frozen=True)
class ExtremeSubclassBarSkill:
    ability_id: int
    base_ability_id: int
    name: str
    skill_line_id: str
    is_ultimate: bool
    morph: int


@dataclass(frozen=True)
class ExtremeSubclassSkillBarResult:
    slot_counts: tuple[tuple[str, int], ...]
    skills: tuple[ExtremeSubclassBarSkill, ...]

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(skill.name for skill in self.skills)


@dataclass(frozen=True)
class ExtremeSubclassTwoBarResult:
    front: ExtremeSubclassSkillBarResult
    back: ExtremeSubclassSkillBarResult


class ExtremeSubclassSkillBarService:
    """Turn abstract subclass slot allocations into canonical legal skill bars.

    Every equipped class skill line contributes its own active abilities and its
    own Ultimate candidates. A subclassed character may therefore use an
    Ultimate from any one of its three equipped class lines on either bar.

    Bar legality is independent: each bar has five normal slots and one Ultimate
    slot, and the same Ultimate may legally be slotted on both bars. There is no
    cross-bar uniqueness rule for abilities or Ultimates.

    Base/morph families still fill only one slot. When BFF has a reviewed
    standing effect for the requested Extreme objective, that morph is preferred
    over a merely alphabetical representative. Percentage effects require an
    explicit reference value before they may influence objective selection.
    Unreviewed skill effects remain neutral rather than guessed from tooltip prose.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self._catalog = self._build_catalog(load_skill_choices(self.database_path))

    @staticmethod
    def canonical_line_id(raw_line: object) -> str | None:
        return _CANONICAL_LINE_BY_TOKEN.get(_line_token(raw_line))

    @classmethod
    def _build_catalog(
        cls,
        rows: list[dict],
    ) -> dict[str, tuple[ExtremeSubclassBarSkill, ...]]:
        by_line: dict[str, dict[tuple[int, int, bool], ExtremeSubclassBarSkill]] = {}
        for row in rows:
            if not is_player_active(row):
                continue
            line_id = cls.canonical_line_id(row.get("skill_line"))
            if line_id is None:
                continue
            ability_id = int(row.get("ability_id") or 0)
            base_id = int(row.get("base_ability_id") or ability_id or 0)
            if ability_id <= 0 or base_id <= 0:
                continue
            ultimate = is_ultimate(row)
            candidate = ExtremeSubclassBarSkill(
                ability_id=ability_id,
                base_ability_id=base_id,
                name=str(row.get("name") or "").strip(),
                skill_line_id=line_id,
                is_ultimate=ultimate,
                morph=int(row.get("morph") or 0),
            )
            if not candidate.name:
                continue
            key = (base_id, candidate.morph, ultimate)
            existing = by_line.setdefault(line_id, {}).get(key)
            if existing is None or cls._preference(candidate) < cls._preference(existing):
                by_line[line_id][key] = candidate

        return {
            line_id: tuple(sorted(values.values(), key=cls._display_key))
            for line_id, values in by_line.items()
        }

    @staticmethod
    def _preference(skill: ExtremeSubclassBarSkill) -> tuple[int, str, int]:
        morph_rank = 0 if skill.morph > 0 else 1
        return (morph_rank, skill.name.casefold(), skill.ability_id)

    @staticmethod
    def _display_key(skill: ExtremeSubclassBarSkill) -> tuple[str, int]:
        return (skill.name.casefold(), skill.ability_id)

    @classmethod
    def _objective_preference(
        cls,
        skill: ExtremeSubclassBarSkill,
        objective_key: str,
        *,
        reference_value: float | None = None,
    ) -> tuple[float, int, str, int]:
        score = ExtremeSkillStandingEffectService.score(
            skill.name,
            objective_key,
            reference_value=reference_value,
        )
        morph_rank, name, ability_id = cls._preference(skill)
        return (-score, morph_rank, name, ability_id)

    def skills_for_line(
        self,
        skill_line_id: str,
        *,
        ultimate: bool,
        objective_key: str = "",
        reference_value: float | None = None,
    ) -> tuple[ExtremeSubclassBarSkill, ...]:
        line = str(skill_line_id or "").strip().casefold()
        rows = tuple(
            skill
            for skill in self._catalog.get(line, ())
            if skill.is_ultimate is bool(ultimate)
        )

        families: dict[int, list[ExtremeSubclassBarSkill]] = {}
        for skill in rows:
            families.setdefault(skill.base_ability_id, []).append(skill)

        selected = [
            min(
                family,
                key=lambda skill: self._objective_preference(
                    skill,
                    objective_key,
                    reference_value=reference_value,
                ),
            )
            for family in families.values()
        ]
        return tuple(
            sorted(
                selected,
                key=lambda skill: self._objective_preference(
                    skill,
                    objective_key,
                    reference_value=reference_value,
                ),
            )
        )

    def materialize(
        self,
        slot_counts: tuple[tuple[str, int], ...],
        *,
        objective_key: str = "",
        reference_value: float | None = None,
    ) -> ExtremeSubclassSkillBarResult | None:
        requested = {
            str(line or "").strip().casefold(): max(0, int(count))
            for line, count in slot_counts
            if str(line or "").strip() and int(count) > 0
        }
        if not requested or sum(requested.values()) != 6:
            return None

        candidates: list[ExtremeSubclassSkillBarResult] = []
        for ultimate_line in sorted(requested):
            ultimates = self.skills_for_line(
                ultimate_line,
                ultimate=True,
                objective_key=objective_key,
                reference_value=reference_value,
            )
            if not ultimates:
                continue

            normal_needed = dict(requested)
            normal_needed[ultimate_line] -= 1
            if normal_needed[ultimate_line] < 0:
                continue

            normals: list[ExtremeSubclassBarSkill] = []
            legal = True
            for line in sorted(normal_needed):
                needed = normal_needed[line]
                if needed <= 0:
                    continue
                choices = self.skills_for_line(
                    line,
                    ultimate=False,
                    objective_key=objective_key,
                    reference_value=reference_value,
                )
                if len(choices) < needed:
                    legal = False
                    break
                normals.extend(choices[:needed])
            if not legal or len(normals) != 5:
                continue

            for ultimate_skill in ultimates:
                skills = tuple((*normals, ultimate_skill))
                candidates.append(
                    ExtremeSubclassSkillBarResult(
                        slot_counts=tuple(sorted(requested.items())),
                        skills=skills,
                    )
                )

        if not candidates:
            return None

        def candidate_key(row: ExtremeSubclassSkillBarResult):
            effect_score = sum(
                ExtremeSkillStandingEffectService.score(
                    skill.name,
                    objective_key,
                    reference_value=reference_value,
                )
                for skill in row.skills
            )
            deterministic = tuple(
                (skill.name.casefold(), skill.ability_id)
                for skill in row.skills
            )
            return (-effect_score, deterministic)

        return min(candidates, key=candidate_key)

    def materialize_two_bars(
        self,
        front_slot_counts: tuple[tuple[str, int], ...],
        back_slot_counts: tuple[tuple[str, int], ...],
        *,
        objective_key: str = "",
        reference_value: float | None = None,
    ) -> ExtremeSubclassTwoBarResult | None:
        """Materialize front/back bars independently.

        This deliberately performs no cross-bar deduplication. ESO allows the
        same active skill or Ultimate on both bars, so legality is checked per
        bar rather than across the character as a whole. Effect stacking is a
        separate build-level concern.
        """
        front = self.materialize(
            front_slot_counts,
            objective_key=objective_key,
            reference_value=reference_value,
        )
        if front is None:
            return None
        back = self.materialize(
            back_slot_counts,
            objective_key=objective_key,
            reference_value=reference_value,
        )
        if back is None:
            return None
        return ExtremeSubclassTwoBarResult(front=front, back=back)
