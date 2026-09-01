"""Verified supplemental skill effects missing from imported ability links.

This registry is intentionally data-only and description-blind at runtime.
Entries are added only after auditing the imported ability rows and confirming
that the mechanic is present in source data but absent from ability_effect_link.

Imported links remain authoritative when they exist. These records supplement,
never replace, linked effects.
"""

from __future__ import annotations

from dataclasses import dataclass

from .character_build.effect_instance import EffectVariant
from .character_build.effect_layer import EffectLayer
from .support_effect_category import SupportEffectCategory
from .support_stacking import StackingBehavior
from .support_target_type import SupportTargetType


@dataclass(frozen=True)
class VerifiedSkillEffect:
    base_ability_id: int
    morph: int
    name: str
    source: str
    magnitude: float | None = None
    duration: float | None = None
    target_type: SupportTargetType | None = None
    category: SupportEffectCategory | None = None
    stacking: StackingBehavior | None = None
    exclusivity_group: str | None = None
    condition: str | None = None

    def to_variant(self) -> EffectVariant:
        return EffectVariant(
            name=self.name,
            layer=EffectLayer.CAST,
            source=self.source,
            magnitude=self.magnitude,
            duration=self.duration,
            target_type=self.target_type,
            category=self.category,
            stacking=self.stacking,
            exclusivity_group=self.exclusivity_group,
            condition=self.condition,
        )


# Audited against data/eso.db with tools/audit_phase5_skill_effect_evidence.py.
# Exact evidence:
# - Combat Prayer base 37243 / morph 2: Minor Resolve, 2974 resistance, 10s.
# - Expansive Frost Cloak base 86122 / morph 1: Major Resolve, 5948 resistance, 20s.
# - Overflowing Altar base 39489 / morph 2: Minor Lifesteal, 600 Health per second, 30s.
_VERIFIED: tuple[VerifiedSkillEffect, ...] = (
    VerifiedSkillEffect(
        base_ability_id=37243,
        morph=2,
        name="minor_resolve",
        source="Combat Prayer",
        magnitude=2974.0,
        duration=10.0,
        target_type=SupportTargetType.GROUP,
        category=SupportEffectCategory.BUFF,
        stacking=StackingBehavior.UNIQUE,
        exclusivity_group="minor_resolve",
    ),
    VerifiedSkillEffect(
        base_ability_id=86122,
        morph=1,
        name="major_resolve",
        source="Expansive Frost Cloak",
        magnitude=5948.0,
        duration=20.0,
        target_type=SupportTargetType.GROUP,
        category=SupportEffectCategory.BUFF,
        stacking=StackingBehavior.UNIQUE,
        exclusivity_group="major_resolve",
    ),
    VerifiedSkillEffect(
        base_ability_id=39489,
        morph=2,
        name="minor_lifesteal",
        source="Overflowing Altar",
        magnitude=600.0,
        duration=30.0,
        target_type=SupportTargetType.ENEMY,
        category=SupportEffectCategory.DEBUFF,
        stacking=StackingBehavior.UNIQUE,
        exclusivity_group="minor_lifesteal",
        condition="damage_affected_enemy",
    ),
)


def verified_skill_effects(
    base_ability_id: int,
    morph: int,
) -> tuple[EffectVariant, ...]:
    return tuple(
        entry.to_variant()
        for entry in _VERIFIED
        if entry.base_ability_id == int(base_ability_id)
        and entry.morph == int(morph)
    )
