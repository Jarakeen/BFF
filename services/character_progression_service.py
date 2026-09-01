from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from services.build_catalog_service import BuildCatalogService


@dataclass(frozen=True)
class CharacterProgression:
    character_id: str
    owned_skill_lines: tuple[str, ...] = ()
    passive_ranks: dict[str, int] | None = None
    passive_cp_points: dict[str, int] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "passive_ranks", dict(self.passive_ranks or {}))
        object.__setattr__(self, "passive_cp_points", dict(self.passive_cp_points or {}))


class CharacterProgressionService:
    """Persist character-owned progression without copying it into builds.

    Present keys are known facts, including an explicit zero. Missing keys are
    unknown/unrecorded and must not be interpreted as zero by calculators.
    """

    def __init__(self, catalog_service: BuildCatalogService) -> None:
        self.catalog_service = catalog_service

    @staticmethod
    def _normalize_names(values: Any) -> list[str]:
        if not isinstance(values, (list, tuple, set)):
            return []
        seen: set[str] = set()
        result: list[str] = []
        for raw in values:
            value = " ".join(str(raw or "").strip().split())
            key = value.casefold()
            if not value or key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result

    @staticmethod
    def _normalize_points(values: Any) -> dict[str, int]:
        if not isinstance(values, dict):
            return {}
        result: dict[str, int] = {}
        seen: set[str] = set()
        for raw_name, raw_points in values.items():
            name = " ".join(str(raw_name or "").strip().split())
            key = name.casefold()
            if not name or key in seen:
                continue
            try:
                points = int(raw_points)
            except (TypeError, ValueError):
                continue
            if points < 0:
                continue
            seen.add(key)
            result[name] = points
        return result

    def get(self, character_id: str) -> CharacterProgression | None:
        character = self.catalog_service.get_character(character_id)
        if character is None:
            return None
        return CharacterProgression(
            character_id=character_id,
            owned_skill_lines=tuple(self._normalize_names(character.get("owned_skill_lines"))),
            passive_ranks=self._normalize_points(character.get("passive_ranks")),
            passive_cp_points=self._normalize_points(character.get("passive_cp_points")),
        )

    def save(
        self,
        *,
        character_id: str,
        owned_skill_lines: list[str] | tuple[str, ...] | set[str],
        passive_ranks: dict[str, int],
        passive_cp_points: dict[str, int],
    ) -> CharacterProgression | None:
        """Replace one character's known progression snapshot atomically."""
        catalog = self.catalog_service.load()
        for index, character in enumerate(catalog["characters"]):
            if character.get("character_id") != character_id:
                continue
            updated = copy.deepcopy(character)
            updated["owned_skill_lines"] = self._normalize_names(owned_skill_lines)
            updated["passive_ranks"] = self._normalize_points(passive_ranks)
            updated["passive_cp_points"] = self._normalize_points(passive_cp_points)
            catalog["characters"][index] = updated
            self.catalog_service.save(catalog)
            return self.get(character_id)
        return None

    def find_character_id(self, *, name: str, gamertag: str) -> str | None:
        wanted = (
            str(gamertag or "").strip().casefold(),
            str(name or "").strip().casefold(),
        )
        for character in self.catalog_service.load()["characters"]:
            candidate = (
                str(character.get("gamertag") or "").strip().casefold(),
                str(character.get("name") or "").strip().casefold(),
            )
            if candidate == wanted:
                value = str(character.get("character_id") or "").strip()
                return value or None
        return None
