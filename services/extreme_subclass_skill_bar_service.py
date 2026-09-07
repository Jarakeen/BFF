from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path

from minmax.character_build.character_class import CLASS_SKILL_LINES
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


class ExtremeSubclassSkillBarService:
    """Turn an abstract subclass slot allocation into one canonical legal bar.

    The service proves only bar materialization. It does not claim that the
    chosen morphs are themselves optimal for the Extreme objective. For each
    base ability family it chooses one deterministic canonical representative,
    preferring a morph over the unmorphed base where available.
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
        by_line: dict[str, dict[tuple[int, bool], ExtremeSubclassBarSkill]] = {}
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
            key = (base_id, ultimate)
            existing = by_line.setdefault(line_id, {}).get(key)
            if existing is None or cls._preference(candidate) < cls._preference(existing):
                by_line[line_id][key] = candidate

        return {
            line_id: tuple(sorted(values.values(), key=cls._display_key))
            for line_id, values in by_line.items()
        }

    @staticmethod
    def _preference(skill: ExtremeSubclassBarSkill) -> tuple[int, str, int]:
        # Prefer a morph over the unmorphed base, then keep selection stable.
        morph_rank = 0 if skill.morph > 0 else 1
        return (morph_rank, skill.name.casefold(), skill.ability_id)

    @staticmethod
    def _display_key(skill: ExtremeSubclassBarSkill) -> tuple[str, int]:
        return (skill.name.casefold(), skill.ability_id)

    def skills_for_line(
        self,
        skill_line_id: str,
        *,
        ultimate: bool,
    ) -> tuple[ExtremeSubclassBarSkill, ...]:
        line = str(skill_line_id or "").strip().casefold()
        return tuple(
            skill
            for skill in self._catalog.get(line, ())
            if skill.is_ultimate is bool(ultimate)
        )

    def materialize(
        self,
        slot_counts: tuple[tuple[str, int], ...],
    ) -> ExtremeSubclassSkillBarResult | None:
        requested = {
            str(line or "").strip().casefold(): max(0, int(count))
            for line, count in slot_counts
            if str(line or "").strip() and int(count) > 0
        }
        if not requested or sum(requested.values()) != 6:
            return None

        # The sixth slot must be an Ultimate. Try each represented line as the
        # Ultimate provider, then choose the first deterministic legal bar.
        candidates: list[ExtremeSubclassSkillBarResult] = []
        for ultimate_line in sorted(requested):
            ultimates = self.skills_for_line(ultimate_line, ultimate=True)
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
                choices = self.skills_for_line(line, ultimate=False)
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
        return min(
            candidates,
            key=lambda row: tuple((skill.name.casefold(), skill.ability_id) for skill in row.skills),
        )
