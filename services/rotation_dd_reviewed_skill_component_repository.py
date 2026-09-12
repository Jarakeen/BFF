from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from minmax.skill_component_repository import SkillComponentRepository


class RotationDDReviewedSkillComponentRepository:
    """Overlay exact reviewed components encountered by DD rotation evidence.

    These rows are reviewed from coefficient-local ``ability.coef_description``
    evidence. They are keyed by exact max-rank ``skill_rank_id`` + coefficient
    number, while durable ability identity remains the canonical lower-snake-case
    skill entity used by the coefficient repository and Rotation Builder.

    Most rows are DD damage components. A DD build may also slot a personal heal;
    reviewed non-damage identity belongs here when it is needed to keep the DD
    evaluator from treating a known heal as unresolved damage evidence.

    ``can_crit=True`` follows the repository's existing ordinary active-skill rule:
    normal skill damage/healing components are crit-eligible; proc/set and special
    damage exceptions are modeled separately.
    """

    _REVIEW_SOURCE = (
        "reviewed coefficient-local damage identity from Corpsebuster DD audit; "
        "ordinary active-skill crit rule"
    )
    _RESOLVING_VIGOR_SOURCE = (
        "reviewed Resolving Vigor self heal-over-time identity; "
        "ordinary active-skill crit rule"
    )

    _REVIEWED: dict[tuple[int, int], SkillComponentClassification] = {
        (7188, 1): SkillComponentClassification(
            skill_rank_id=7188,
            coefficient_number=1,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="poison",
            is_dot=False,
            is_aoe=False,
            can_crit=True,
            source=_REVIEW_SOURCE,
            confidence=1.0,
        ),
        (7308, 1): SkillComponentClassification(
            skill_rank_id=7308,
            coefficient_number=1,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="frost",
            is_dot=True,
            is_aoe=True,
            can_crit=True,
            source=_REVIEW_SOURCE,
            confidence=1.0,
        ),
        (7308, 2): SkillComponentClassification(
            skill_rank_id=7308,
            coefficient_number=2,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="frost",
            is_dot=False,
            is_aoe=True,
            can_crit=True,
            source=_REVIEW_SOURCE,
            confidence=1.0,
        ),
        (7368, 1): SkillComponentClassification(
            skill_rank_id=7368,
            coefficient_number=1,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="disease",
            is_dot=True,
            is_aoe=True,
            can_crit=True,
            source=_REVIEW_SOURCE,
            confidence=1.0,
        ),
        (7368, 2): SkillComponentClassification(
            skill_rank_id=7368,
            coefficient_number=2,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="disease",
            is_dot=False,
            is_aoe=True,
            can_crit=True,
            source=_REVIEW_SOURCE,
            confidence=1.0,
        ),
        (7224, 1): SkillComponentClassification(
            skill_rank_id=7224,
            coefficient_number=1,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="disease",
            is_dot=False,
            is_aoe=True,
            can_crit=True,
            source=_REVIEW_SOURCE,
            confidence=1.0,
        ),
        (6053, 1): SkillComponentClassification(
            skill_rank_id=6053,
            coefficient_number=1,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="physical",
            is_dot=False,
            is_aoe=True,
            can_crit=True,
            source=_REVIEW_SOURCE,
            confidence=1.0,
        ),
        (6053, 2): SkillComponentClassification(
            skill_rank_id=6053,
            coefficient_number=2,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="physical",
            is_dot=True,
            is_aoe=True,
            can_crit=True,
            source=_REVIEW_SOURCE,
            confidence=1.0,
        ),
        (7212, 1): SkillComponentClassification(
            skill_rank_id=7212,
            coefficient_number=1,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="physical",
            is_dot=True,
            is_aoe=False,
            can_crit=True,
            source=_REVIEW_SOURCE,
            confidence=1.0,
        ),
        (5756, 1): SkillComponentClassification(
            skill_rank_id=5756,
            coefficient_number=1,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="flame",
            is_dot=False,
            is_aoe=True,
            can_crit=True,
            source=_REVIEW_SOURCE,
            confidence=1.0,
        ),
        (5756, 2): SkillComponentClassification(
            skill_rank_id=5756,
            coefficient_number=2,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="flame",
            is_dot=True,
            is_aoe=True,
            can_crit=True,
            source=_REVIEW_SOURCE,
            confidence=1.0,
        ),
        (5134, 1): SkillComponentClassification(
            skill_rank_id=5134,
            coefficient_number=1,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="physical",
            is_dot=False,
            is_aoe=True,
            can_crit=True,
            source=_REVIEW_SOURCE,
            confidence=1.0,
        ),
        (5134, 2): SkillComponentClassification(
            skill_rank_id=5134,
            coefficient_number=2,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="physical",
            is_dot=True,
            is_aoe=True,
            can_crit=True,
            source=_REVIEW_SOURCE,
            confidence=1.0,
        ),
        (4419, 1): SkillComponentClassification(
            skill_rank_id=4419,
            coefficient_number=1,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="flame",
            is_dot=False,
            is_aoe=True,
            can_crit=True,
            source=_REVIEW_SOURCE,
            confidence=1.0,
        ),
        (4419, 2): SkillComponentClassification(
            skill_rank_id=4419,
            coefficient_number=2,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="flame",
            is_dot=True,
            is_aoe=True,
            can_crit=True,
            source=_REVIEW_SOURCE,
            confidence=1.0,
        ),
        (6641, 1): SkillComponentClassification(
            skill_rank_id=6641,
            coefficient_number=1,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=True,
            is_aoe=False,
            can_crit=True,
            source=_RESOLVING_VIGOR_SOURCE,
            confidence=1.0,
        ),
    }

    def __init__(
        self,
        database_path: str | Path,
        *,
        base_repository: SkillComponentRepository | object | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.base_repository = base_repository or SkillComponentRepository(database_path)

    @staticmethod
    def _merge(
        base: SkillComponentClassification | None,
        reviewed: SkillComponentClassification,
    ) -> SkillComponentClassification:
        if base is None:
            return reviewed
        return replace(
            base,
            effect_kind=reviewed.effect_kind,
            damage_type=reviewed.damage_type,
            is_dot=reviewed.is_dot,
            is_aoe=reviewed.is_aoe,
            can_crit=reviewed.can_crit,
            source=reviewed.source,
            confidence=reviewed.confidence,
        )

    def get_for_skill_rank(self, skill_rank_id: int) -> tuple[SkillComponentClassification, ...]:
        rank_id = int(skill_rank_id)
        base = {
            int(component.coefficient_number): component
            for component in self.base_repository.get_for_skill_rank(rank_id)
        }
        reviewed = {
            coefficient_number: component
            for (reviewed_rank_id, coefficient_number), component in self._REVIEWED.items()
            if reviewed_rank_id == rank_id
        }
        if not reviewed:
            return tuple(base[number] for number in sorted(base))

        numbers = sorted(set(base) | set(reviewed))
        return tuple(
            self._merge(base.get(number), reviewed[number])
            if number in reviewed
            else base[number]
            for number in numbers
        )

    def get_component(
        self,
        skill_rank_id: int,
        coefficient_number: int,
    ) -> SkillComponentClassification | None:
        requested = int(coefficient_number)
        for component in self.get_for_skill_rank(skill_rank_id):
            if int(component.coefficient_number) == requested:
                return component
        return None


__all__ = ["RotationDDReviewedSkillComponentRepository"]
