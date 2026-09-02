from __future__ import annotations

"""Read-only Phase 10 discovery audit for encounter-capability candidates.

Text matching here is intentionally a *review queue*, never runtime truth. Candidate
abilities are resolved through SkillEffectRepository so reviewers can promote only
verified exact EffectVariant.name identities into the Phase 10 capability map.

The audit also preserves stable ability metadata and the exact matched source text.
That lets reviewers verify a mechanic against canonical base ability / morph identity
rather than accidentally promoting one rank-specific ability id.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from minmax.skill_effect_repository import SkillEffectRepository


_CAPABILITY_TERMS: dict[str, tuple[str, ...]] = {
    "cleanse": (
        "cleanse",
        "purge",
        "remove negative effect",
        "remove negative effects",
        "negative effect removed",
    ),
    "interrupt": (
        "interrupt",
        "interrupts",
        "interrupted",
    ),
}


@dataclass(frozen=True)
class EncounterCapabilityCandidate:
    capability_type: str
    ability_id: int
    ability_name: str
    base_ability_id: int | None
    morph: int | None
    rank: int | None
    class_type: str
    skill_line: str
    matched_term: str
    matched_field: str
    matched_source_text: str
    resolved_effect_names: tuple[str, ...]
    resolved_effect_sources: tuple[str, ...]


class EncounterCapabilityCandidateAudit:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.skill_effects = SkillEffectRepository(self.database_path)

    @staticmethod
    def supported_capabilities() -> tuple[str, ...]:
        return tuple(_CAPABILITY_TERMS)

    @staticmethod
    def _optional_select(columns: set[str], name: str, fallback: str) -> str:
        return f'"{name}"' if name in columns else f"{fallback} AS \"{name}\""

    def candidates(self, capability_type: str) -> tuple[EncounterCapabilityCandidate, ...]:
        if capability_type not in _CAPABILITY_TERMS:
            raise ValueError(
                f"Unsupported capability_type {capability_type!r}; expected one of "
                f"{', '.join(_CAPABILITY_TERMS)}"
            )
        if not self.database_path.exists():
            raise FileNotFoundError(self.database_path)

        with sqlite3.connect(self.database_path) as db:
            columns = {
                str(row[1])
                for row in db.execute("PRAGMA table_info(ability)").fetchall()
            }
            if not {"ability_id", "name"}.issubset(columns):
                raise ValueError("ability table must contain ability_id and name")

            searchable = ["name"]
            for candidate in (
                "description",
                "tooltip",
                "raw_description",
                "raw_tooltip",
            ):
                if candidate in columns:
                    searchable.append(candidate)

            selected = [
                "ability_id",
                "name",
                self._optional_select(columns, "base_ability_id", "NULL"),
                self._optional_select(columns, "morph", "NULL"),
                self._optional_select(columns, "rank", "NULL"),
                self._optional_select(columns, "class_type", "''"),
                self._optional_select(columns, "skill_line", "''"),
            ]
            selected.extend(
                f'COALESCE("{column}", \'\') AS "{column}"'
                for column in searchable[1:]
            )
            rows = db.execute(
                f"SELECT {', '.join(selected)} FROM ability ORDER BY ability_id"
            ).fetchall()

        found: list[EncounterCapabilityCandidate] = []
        seen: set[tuple[int, str]] = set()
        terms = _CAPABILITY_TERMS[capability_type]

        for row in rows:
            ability_id = int(row[0])
            ability_name = str(row[1] or "").strip()
            base_ability_id = int(row[2]) if row[2] is not None else None
            morph = int(row[3]) if row[3] is not None else None
            rank = int(row[4]) if row[4] is not None else None
            class_type = str(row[5] or "").strip()
            skill_line = str(row[6] or "").strip()

            values = {"name": ability_name}
            for index, column in enumerate(searchable[1:], start=7):
                values[column] = str(row[index] or "").strip()

            match: tuple[str, str] | None = None
            for field_name in searchable:
                text = values[field_name].casefold()
                for term in terms:
                    if term.casefold() in text:
                        match = (term, field_name)
                        break
                if match is not None:
                    break
            if match is None:
                continue

            key = (ability_id, capability_type)
            if key in seen:
                continue
            seen.add(key)

            effects = self.skill_effects.resolve(ability_id)
            found.append(
                EncounterCapabilityCandidate(
                    capability_type=capability_type,
                    ability_id=ability_id,
                    ability_name=ability_name,
                    base_ability_id=base_ability_id,
                    morph=morph,
                    rank=rank,
                    class_type=class_type,
                    skill_line=skill_line,
                    matched_term=match[0],
                    matched_field=match[1],
                    matched_source_text=values[match[1]],
                    resolved_effect_names=tuple(dict.fromkeys(effect.name for effect in effects)),
                    resolved_effect_sources=tuple(dict.fromkeys(effect.source for effect in effects)),
                )
            )

        return tuple(found)
