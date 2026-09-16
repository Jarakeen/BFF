from __future__ import annotations

"""Classify the selected H1 heal for candidate-specific gear scopes.

This service deliberately owns identity only. It does not apply gear arithmetic and
it does not infer missing tags from ability names. Class/weapon-line identity comes
from canonical ability metadata or an already-materialized heal candidate. AoE
identity comes from reviewed per-component classification for the selected max-rank
HEAL components; incomplete or conflicting component evidence remains unresolved.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from minmax.skill_coefficient_repository import ability_entity_id
from minmax.skill_component_classification import SkillEffectKind
from minmax.skill_component_repository import SkillComponentRepository
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

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        component_repository: SkillComponentRepository | None = None,
    ) -> None:
        self.database_path = Path(database_path) if database_path is not None else None
        self.components = component_repository or (
            SkillComponentRepository(self.database_path)
            if self.database_path is not None
            else None
        )
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

    def _canonical_aoe_for_rank(self, skill_rank_id: int, name: str) -> tuple[bool | None, str | None]:
        if self.components is None:
            return None, None
        heals = tuple(
            component
            for component in self.components.get_for_skill_rank(int(skill_rank_id))
            if component.effect_kind is SkillEffectKind.HEAL
        )
        if not heals:
            return None, None
        values = tuple(component.is_aoe for component in heals)
        if any(value is None for value in values):
            return None, (
                f"canonical HEAL component AoE evidence incomplete for {name}: "
                + ", ".join(
                    f"coef{component.coefficient_number}={component.is_aoe!r}"
                    for component in heals
                )
            )
        unique = {bool(value) for value in values}
        if len(unique) != 1:
            return None, (
                f"canonical HEAL component AoE evidence conflicts for {name}: "
                + ", ".join(
                    f"coef{component.coefficient_number}={component.is_aoe!r}"
                    for component in heals
                )
            )
        resolved = next(iter(unique))
        return resolved, (
            f"canonical HEAL component AoE classification for {name}: "
            + ", ".join(
                f"coef{component.coefficient_number}={component.is_aoe!r}"
                for component in heals
            )
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
            required = ("ability", "skill_rank")
            if any(
                connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                ).fetchone()
                is None
                for table in required
            ):
                return None
            rows = connection.execute(
                """
                SELECT
                    sr.id,
                    COALESCE(sr.rank, 0),
                    COALESCE(a.name, ''),
                    COALESCE(a.skill_line, ''),
                    COALESCE(a.class_type, '')
                FROM skill_rank sr
                JOIN ability a ON a.ability_id = sr.ability_id
                WHERE COALESCE(a.is_player, 0) <> 0
                  AND COALESCE(a.is_passive, 0) = 0
                  AND COALESCE(a.name, '') <> ''
                """
            ).fetchall()

        matches = [
            (
                int(skill_rank_id),
                int(rank or 0),
                str(name).strip(),
                str(skill_line).strip(),
                str(class_type).strip(),
            )
            for skill_rank_id, rank, name, skill_line, class_type in rows
            if ability_entity_id(str(name)) == key
        ]
        if not matches:
            result = None
        else:
            skill_rank_id, _rank, name, skill_line, class_type = sorted(
                matches,
                key=lambda row: (
                    -row[1],
                    row[4].casefold(),
                    row[3].casefold(),
                    row[2].casefold(),
                    row[0],
                ),
            )[0]
            resolved_area = area_of_effect
            resolved_area_evidence = area_evidence
            if resolved_area is None and not resolved_area_evidence:
                resolved_area, resolved_area_evidence = self._canonical_aoe_for_rank(
                    skill_rank_id,
                    name,
                )
            result = self._from_identity(
                name=name,
                skill_line=skill_line,
                class_type=class_type,
                area_of_effect=resolved_area,
                area_evidence=resolved_area_evidence,
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
                area_evidence
                or f"{name}: area-of-effect identity has no canonical H1 evidence"
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
