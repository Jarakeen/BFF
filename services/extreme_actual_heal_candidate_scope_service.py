from __future__ import annotations

"""Classify the selected H1 heal for candidate-specific gear scopes.

This service deliberately owns identity only. It does not apply gear arithmetic and
it does not infer missing tags from ability names. Class/weapon-line identity comes
from the canonical heal candidate record; AoE remains unresolved until an
authoritative ability-shape source is wired.
"""

from dataclasses import dataclass

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

    @classmethod
    def resolve(
        cls,
        candidate: ExtremeHealSkillCandidate,
        *,
        area_of_effect: bool | None = None,
        area_evidence: str | None = None,
    ) -> ExtremeActualHealCandidateScope:
        line_id = canonical_class_skill_line_id(candidate.skill_line)
        is_class = bool(str(candidate.class_type or "").strip())
        is_weapon = line_id in _WEAPON_LINES
        is_restoration = line_id == "restoration_staff"

        evidence = [
            f"skill_line={candidate.skill_line or '(empty)'} canonical_line={line_id or '(empty)'}",
            f"class_type={candidate.class_type or '(none)'}",
        ]
        unresolved: list[str] = []
        if area_of_effect is None:
            unresolved.append(
                f"{candidate.name}: area-of-effect identity has no canonical H1 evidence"
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
