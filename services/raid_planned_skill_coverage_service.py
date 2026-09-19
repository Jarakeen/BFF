from __future__ import annotations

"""Project explicit Raid Plan skill/class choices into planned Coverage evidence.

This service answers planning availability only. It uses reviewed canonical skill effect
variants and reviewed class passive provider relationships, filters out self-only sources,
and marks every accepted source Conditional because exact activation/uptime belongs to
Rotation/Raid Review rather than planning Coverage.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from minmax.skill_effect_repository import SkillEffectRepository
from minmax.support_target_type import SupportTargetType
from services.passive_effect_provider_reference_service import (
    PassiveEffectProviderReferenceService,
)
from services.saved_build_capability_service import RaidCoverageSnapshot


_ALLOWED_TARGETS = {
    SupportTargetType.ALLY,
    SupportTargetType.SELF_OR_ALLY,
    SupportTargetType.GROUP,
    SupportTargetType.ENEMY,
}


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _canonical(value: object) -> str:
    return "_".join(
        _clean(value).casefold().replace("'", "").replace("-", " ").split()
    )


@dataclass(frozen=True)
class PlannedSkillCoverageProvider:
    seat_id: str
    provider_label: str
    eso_class: str | None = None
    skills: tuple[str, ...] = ()


class RaidPlannedSkillCoverageService:
    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.skills = SkillEffectRepository(self.database_path)
        self.passives = PassiveEffectProviderReferenceService()
        self._ability_id_cache: dict[tuple[str, str], int | None] = {}
        self._skill_line_cache: dict[tuple[str, str], str | None] = {}

    def _ability_id(self, skill_name: str, eso_class: str | None) -> int | None:
        key = (_clean(skill_name).casefold(), _clean(eso_class).casefold())
        if key in self._ability_id_cache:
            return self._ability_id_cache[key]
        if not self.database_path.exists():
            self._ability_id_cache[key] = None
            return None
        try:
            with sqlite3.connect(self.database_path) as db:
                columns = {
                    str(row[1])
                    for row in db.execute("PRAGMA table_info(ability)").fetchall()
                }
                if not {"ability_id", "name"}.issubset(columns):
                    result = None
                else:
                    clauses = ["lower(trim(name)) = lower(trim(?))"]
                    params: list[object] = [skill_name]
                    if eso_class and "class_type" in columns:
                        clauses.append(
                            "(trim(coalesce(class_type,'')) = '' OR "
                            "lower(trim(class_type)) = lower(trim(?)))"
                        )
                        params.append(eso_class)
                    order = (
                        "rank DESC, morph DESC, ability_id DESC"
                        if {"rank", "morph"}.issubset(columns)
                        else "ability_id DESC"
                    )
                    row = db.execute(
                        f"SELECT ability_id FROM ability WHERE {' AND '.join(clauses)} "
                        f"ORDER BY {order} LIMIT 1",
                        params,
                    ).fetchone()
                    result = int(row[0]) if row else None
        except sqlite3.Error:
            result = None
        self._ability_id_cache[key] = result
        return result

    def _skill_line(self, skill_name: str, eso_class: str | None) -> str | None:
        key = (_clean(skill_name).casefold(), _clean(eso_class).casefold())
        if key in self._skill_line_cache:
            return self._skill_line_cache[key]
        if not self.database_path.exists():
            self._skill_line_cache[key] = None
            return None
        try:
            with sqlite3.connect(self.database_path) as db:
                columns = {
                    str(row[1])
                    for row in db.execute("PRAGMA table_info(ability)").fetchall()
                }
                if not {"name", "skill_line"}.issubset(columns):
                    result = None
                else:
                    clauses = ["lower(trim(name)) = lower(trim(?))"]
                    params: list[object] = [skill_name]
                    if eso_class and "class_type" in columns:
                        clauses.append(
                            "(trim(coalesce(class_type,'')) = '' OR "
                            "lower(trim(class_type)) = lower(trim(?)))"
                        )
                        params.append(eso_class)
                    row = db.execute(
                        f"SELECT skill_line FROM ability WHERE {' AND '.join(clauses)} "
                        "AND trim(coalesce(skill_line,'')) <> '' LIMIT 1",
                        params,
                    ).fetchone()
                    result = _clean(row[0]) if row else None
        except sqlite3.Error:
            result = None
        self._skill_line_cache[key] = result
        return result

    @staticmethod
    def _display_by_key(effect_names: tuple[str, ...]) -> dict[str, str]:
        return {_canonical(name): name for name in effect_names}

    def effects_for_provider(
        self,
        provider: PlannedSkillCoverageProvider,
        *,
        effect_names: tuple[str, ...],
    ) -> tuple[tuple[str, str], ...]:
        """Return (effect display name, source description) pairs."""
        display = self._display_by_key(effect_names)
        found: list[tuple[str, str]] = []

        for skill_name in provider.skills:
            ability_id = self._ability_id(skill_name, provider.eso_class)
            if ability_id is None:
                continue
            for effect in self.skills.resolve(ability_id):
                if effect.target_type not in _ALLOWED_TARGETS:
                    continue
                effect_name = display.get(_canonical(effect.name))
                if effect_name is None:
                    continue
                found.append((effect_name, f"skill: {_clean(skill_name)}"))

        class_name = _clean(provider.eso_class).casefold()
        planned_skill_lines = {
            _clean(line).casefold()
            for line in (
                self._skill_line(skill_name, provider.eso_class)
                for skill_name in provider.skills
            )
            if _clean(line)
        }
        if class_name and planned_skill_lines:
            for passive in self.passives.all():
                if _clean(passive.eso_class).casefold() != class_name:
                    continue
                if _clean(passive.skill_line).casefold() not in planned_skill_lines:
                    continue
                target = _clean(passive.target).casefold()
                if not any(token in target for token in ("group", "ally", "allies", "enemy")):
                    continue
                effect_name = display.get(_canonical(passive.effect_name))
                if effect_name is None:
                    continue
                found.append((effect_name, f"class passive: {passive.passive_name}"))

        return tuple(dict.fromkeys(found))

    def overlay(
        self,
        snapshot: RaidCoverageSnapshot,
        providers: tuple[PlannedSkillCoverageProvider, ...],
        *,
        effect_names: tuple[str, ...],
    ) -> RaidCoverageSnapshot:
        status = dict(snapshot.status)
        static = {name: list(values) for name, values in snapshot.providers.items()}
        conditional = {
            name: list(values)
            for name, values in snapshot.conditional_providers.items()
        }
        for name in effect_names:
            status.setdefault(name, "unverified")
            static.setdefault(name, [])
            conditional.setdefault(name, [])

        for provider in providers:
            label = _clean(provider.provider_label) or provider.seat_id
            for effect_name, source in self.effects_for_provider(
                provider,
                effect_names=effect_names,
            ):
                evidence = f"{label} [planned: {source}]"
                if evidence not in conditional[effect_name]:
                    conditional[effect_name].append(evidence)

        for name in effect_names:
            if static.get(name):
                status[name] = "available"
            elif conditional.get(name):
                status[name] = "conditional"

        return RaidCoverageSnapshot(status, static, conditional)


__all__ = [
    "PlannedSkillCoverageProvider",
    "RaidPlannedSkillCoverageService",
]
