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
#   The same tooltip grants Minor Berserk to the caster and allies for 10s;
#   the imported generic "berserk" link is self-targeted and cannot prove group coverage.
# - Expansive Frost Cloak base 86122 / morph 1: Major Resolve, 5948 resistance, 20s.
# - Overflowing Altar base 39489 / morph 2: Minor Lifesteal, 600 Health per second, 30s.
#
# Current U50 source review also confirms the following self-applicable Minor Intellect
# and Minor Endurance effects are present in the ability tooltips but absent from
# ability_effect_link:
# - Arcanist's Domain base 183555 / morph 0: Minor Intellect + Minor Endurance, 20s.
# - Enchanted Growth base 85536 / morph 1: Minor Intellect + Minor Endurance, 20s after healing self.
# - Refreshing Path base 33195 / morph 2: Minor Intellect + Minor Endurance, 10s area with 4s linger.
# - Regenerative Ward base 28418 / morph 2: Minor Intellect + Minor Endurance, 10s.
# - Restoring Aura base 26209 / morph 0: Minor Intellect + Minor Endurance, 20s and while slotted.
#
# These supplemental variants model the caster-side application used by Extreme
# self-stat snapshots. Group/ally coverage remains owned by encounter/support layers.
_VERIFIED: tuple[VerifiedSkillEffect, ...] = (
    VerifiedSkillEffect(
        base_ability_id=37243,
        morph=2,
        name="minor_berserk",
        source="Combat Prayer",
        duration=10.0,
        target_type=SupportTargetType.GROUP,
        category=SupportEffectCategory.BUFF,
        stacking=StackingBehavior.UNIQUE,
        exclusivity_group="minor_berserk",
    ),
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
    VerifiedSkillEffect(base_ability_id=183555, morph=0, name="minor_intellect", source="Arcanist's Domain", magnitude=0.15, duration=20.0, target_type=SupportTargetType.SELF, category=SupportEffectCategory.BUFF, stacking=StackingBehavior.UNIQUE, exclusivity_group="minor_intellect"),
    VerifiedSkillEffect(base_ability_id=85536, morph=1, name="minor_intellect", source="Enchanted Growth", magnitude=0.15, duration=20.0, target_type=SupportTargetType.SELF, category=SupportEffectCategory.BUFF, stacking=StackingBehavior.UNIQUE, exclusivity_group="minor_intellect"),
    VerifiedSkillEffect(base_ability_id=33195, morph=2, name="minor_intellect", source="Refreshing Path", magnitude=0.15, duration=10.0, target_type=SupportTargetType.SELF, category=SupportEffectCategory.BUFF, stacking=StackingBehavior.UNIQUE, exclusivity_group="minor_intellect"),
    VerifiedSkillEffect(base_ability_id=28418, morph=2, name="minor_intellect", source="Regenerative Ward", magnitude=0.15, duration=10.0, target_type=SupportTargetType.SELF, category=SupportEffectCategory.BUFF, stacking=StackingBehavior.UNIQUE, exclusivity_group="minor_intellect"),
    VerifiedSkillEffect(base_ability_id=26209, morph=0, name="minor_intellect", source="Restoring Aura", magnitude=0.15, duration=20.0, target_type=SupportTargetType.SELF, category=SupportEffectCategory.BUFF, stacking=StackingBehavior.UNIQUE, exclusivity_group="minor_intellect"),
    VerifiedSkillEffect(base_ability_id=183555, morph=0, name="minor_endurance", source="Arcanist's Domain", magnitude=0.15, duration=20.0, target_type=SupportTargetType.SELF, category=SupportEffectCategory.BUFF, stacking=StackingBehavior.UNIQUE, exclusivity_group="minor_endurance"),
    VerifiedSkillEffect(base_ability_id=85536, morph=1, name="minor_endurance", source="Enchanted Growth", magnitude=0.15, duration=20.0, target_type=SupportTargetType.SELF, category=SupportEffectCategory.BUFF, stacking=StackingBehavior.UNIQUE, exclusivity_group="minor_endurance"),
    VerifiedSkillEffect(base_ability_id=33195, morph=2, name="minor_endurance", source="Refreshing Path", magnitude=0.15, duration=10.0, target_type=SupportTargetType.SELF, category=SupportEffectCategory.BUFF, stacking=StackingBehavior.UNIQUE, exclusivity_group="minor_endurance"),
    VerifiedSkillEffect(base_ability_id=28418, morph=2, name="minor_endurance", source="Regenerative Ward", magnitude=0.15, duration=10.0, target_type=SupportTargetType.SELF, category=SupportEffectCategory.BUFF, stacking=StackingBehavior.UNIQUE, exclusivity_group="minor_endurance"),
    VerifiedSkillEffect(base_ability_id=26209, morph=0, name="minor_endurance", source="Restoring Aura", magnitude=0.15, duration=20.0, target_type=SupportTargetType.SELF, category=SupportEffectCategory.BUFF, stacking=StackingBehavior.UNIQUE, exclusivity_group="minor_endurance"),
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
