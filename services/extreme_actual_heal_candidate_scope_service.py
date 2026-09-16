from __future__ import annotations

"""Classify the selected H1 heal for candidate-specific gear scopes.

This service deliberately owns identity only. It does not apply gear arithmetic and
it does not infer missing tags from ability names. Class/weapon-line identity comes
from canonical ability metadata or an already-materialized heal candidate; AoE
remains unresolved until an authoritative ability-shape source is wired.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from minmax.skill_coefficient_repository import ability_entity_id
from services.extreme_heal_class_route_service import canonical_class_skill_line_id
from services.extreme_heal_skill_candidate_service import ExtremeHealSkillCandidate


_WEAPON_LINES = frozenset(
    {
        "one_hand_and_shield",
        "dual_wield",
        "two_handed",
        "bow",
        "destruction_staff",
        "restoration_staff",
    }
)


@dataclass(frozen=True)
class ExtremeActualHealCandidateScope:
    is_class_ability: bool
    is_weapon_skill_ability: bool
    is_restoration_staff_ability: bool
    is_area_of_effect: bool | None
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


class ExtremeActualHealCandidateScopeService:
    """Resolve candidate-heal scope without broad tooltip guessing."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = Path(database_path) if database_path is not None else None
        self._entity_cache: dict[str, ExtremeActualHealCandidateScope | None] = {}

    @classmethod
    def resolve(
        cls,
        candidate: ExtremeHealSkillCandidate,
        *,
        area_of_effect: bool | None = None,
        area_evidence: str | None = None,
    ) -> ExtremeActualHealCandidateScope:
        return cls._from_identity(
            name=candidate.name,
            skill_line=candidate.skill_line,
            class_type=candidate.class_type,
            area_of_effect=area_of_effect,
            area_evidence=area_evidence,
        )

    def resolve_entity(
        self,
        entity_id: str,
        *,
        area_of_effect: bool | None = None,
        area_evidence: str | None = None,
    ) -> ExtremeActualHealCandidateScope | None:
        key = ability_entity_id(entity_id)
        if not key or self.database_path is None or not self.database_path.exists():
            return None
        if area_of_effect is None and not area_evidence and key in self._entity_cache:
            return self._entity_cache[key]

        with sqlite3.connect(self.database_path) as connection:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ability'"
            ).fetchone()
            if table is None:
                return None
            rows = connection.execute(
                """
                SELECT COALESCE(name, ''), COALESCE(skill_line, ''), COALESCE(class_type, '')
                FROM ability
                WHERE COALESCE(is_player, 0) <> 0
                  AND COALESCE(is_passive, 0) = 0
                  AND COALESCE(name, '') <> ''
                """
            ).fetchall()

        matches = [
            (str(name).strip(), str(skill_line).strip(), str(class_type).strip())
            for name, skill_line, class_type in rows
            if ability_entity_id(str(name)) == key
        ]
        if not matches:
            result = None
        else:
            name, skill_line, class_type = sorted(
                matches,
                key=lambda row: (
                    row[2].casefold(),
                    row[1].casefold(),
                    row[0].casefold(),
                ),
            )[0]
            result = self._from_identity(
                name=name,
                skill_line=skill_line,
                class_type=class_type,
                area_of_effect=area_of_effect,
                area_evidence=area_evidence,
            )
        if area_of_effect is None and not area_evidence:
            self._entity_cache[key] = result
        return result

    @staticmethod
    def _from_identity(
        *,
        name: str,
        skill_line: str,
        class_type: str,
        area_of_effect: bool | None,
        area_evidence: str | None,
    ) -> ExtremeActualHealCandidateScope:
        line_id = canonical_class_skill_line_id(skill_line)
        is_class = bool(str(class_type or "").strip())
        is_weapon = line_id in _WEAPON_LINES
        is_restoration = line_id == "restoration_staff"

        evidence = [
            f"skill_line={skill_line or '(empty)'} canonical_line={line_id or '(empty)'}",
            f"class_type={class_type or '(none)'}",
        ]
        unresolved: list[str] = []
        if area_of_effect is None:
            unresolved.append(
                f"{name}: area-of-effect identity has no canonical H1 evidence"
            )
        elif area_evidence:
            evidence.append(str(area_evidence))

        return ExtremeActualHealCandidateScope(
            is_class_ability=is_class,
            is_weapon_skill_ability=is_weapon,
            is_restoration_staff_ability=is_restoration,
            is_area_of_effect=area_of_effect,
            evidence=tuple(evidence),
            unresolved=tuple(unresolved),
        )


__all__ = [
    "ExtremeActualHealCandidateScope",
    "ExtremeActualHealCandidateScopeService",
]
