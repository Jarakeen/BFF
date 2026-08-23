from __future__ import annotations

import re

from .combat_effect_repository import (
    CombatEffectInteractionRecord,
    CombatEffectRecord,
    CombatEffectRepository,
)
from .effects import EffectUnit
from .support_effect import SupportEffect
from .support_effect_category import SupportEffectCategory
from .support_effect_registry import SupportEffectRegistry
from .support_effect_trigger import SupportEffectTrigger
from .support_stacking import StackingBehavior
from .support_target_type import SupportTargetType


def _slugify(name: str) -> str:
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


class CombatEffectSupportResolver:
    """
    Resolves the ESO database's canonical combat_effect catalog - status
    effects such as Chilled and Burning, and what they cause, such as
    Chilled -> Minor Brittle - into SupportEffects.

        ESO database
            -> CombatEffectRepository
            -> CombatEffectSupportResolver
            -> SupportEffectRegistry

    This is catalog-level, not Build-specific: it describes what the
    game's baseline status-effect system CAN provide, not what a
    particular player's build actually applies during a fight, and not
    proc chance or observed combat uptime. Connecting specific abilities/
    enchantments to these statuses (via the ability_combat_effect table)
    is future work, as is anything ESO-Logs-based.

    Frost damage is never automatically converted into Chilled or
    Brittle here - the chain is only ever reconstructed from what the
    database's trigger/interaction rows actually say. If a status has no
    interaction rows, only the primary status SupportEffect is produced.

    Known, deliberate limitations (documented rather than guessed
    around):

    - `combat_effect_interaction.target_scope` values this resolver can
      confidently place on the self/ally/group/enemy axis are "Target"
      (-> ENEMY), "Caster" and "Attacker" (-> SELF). Any other scope
      (e.g. "Players damaging target") is not resolved into a
      SupportEffect and is skipped rather than guessed at.
    - Per-mechanic fields like damage_amplification, penetration, and
      healing_contribution are only populated when the schema gives an
      explicit, structural signal for them. Today that is limited to
      `resistance_reduction`, which is set when `target_unit ==
      "resistance"`. Effects such as "Minor Vulnerability" or "Minor
      Maim" are resolved with their generic magnitude/unit/duration/
      condition data, but this resolver does not assert what they
      mechanically do beyond that - doing so would mean encoding ESO
      tooltip knowledge that isn't actually present in this table.
    - `combat_effect.tick_interval` and `immunity_duration` have no
      corresponding SupportEffect field yet and are not carried over.
    - `role_relevance` is always left empty; nothing in this data
      source ties an effect to DD/healer/tank.
    - `uptime` is left at the SupportEffect default (1.0), consistent
      with how the weapon-enchantment support resolver already treats
      "what this source CAN provide" - it is not an observed combat
      uptime. ESO Logs data will refine this in a future task.
    """

    SCOPE_TARGET_TYPES: dict[str, SupportTargetType] = {
        "Target": SupportTargetType.ENEMY,
        "Caster": SupportTargetType.SELF,
        "Attacker": SupportTargetType.SELF,
    }

    CATEGORY_MAP: dict[str, SupportEffectCategory] = {
        "Status": SupportEffectCategory.STATUS,
        "Combat": SupportEffectCategory.OTHER,
        "Other": SupportEffectCategory.OTHER,
    }

    def __init__(self, repository: CombatEffectRepository):
        self.repository = repository

    def resolve(self) -> SupportEffectRegistry:
        registry = SupportEffectRegistry()

        for record in self.repository.get_all():
            registry.add(self._primary_effect(record))

            for interaction in record.interactions:
                support_effect = self._interaction_effect(
                    record,
                    interaction,
                )
                if support_effect is not None:
                    registry.add(support_effect)

        return registry

    def _primary_effect(self, record: CombatEffectRecord) -> SupportEffect:
        trigger = self._trigger(record)

        source = record.name
        if trigger is not None and record.triggers[0].damage_type:
            source = f"{record.triggers[0].damage_type} Damage"

        category = self.CATEGORY_MAP.get(
            record.category,
            SupportEffectCategory.OTHER,
        )

        stacking = (
            StackingBehavior.STACKS
            if record.stack_max and record.stack_max > 1
            else StackingBehavior.UNIQUE
        )

        applies_status = (
            record.name if record.category == "Status" else None
        )

        return SupportEffect(
            source=source,
            name=record.name,
            category=category,
            effect_type=_slugify(record.name),
            target_type=SupportTargetType.ENEMY,
            duration=record.duration,
            stacking=stacking,
            trigger=trigger,
            applies_status=applies_status,
        )

    def _trigger(
        self,
        record: CombatEffectRecord,
    ) -> SupportEffectTrigger | None:
        if not record.triggers:
            return None

        trigger_row = record.triggers[0]

        if trigger_row.trigger_type == "Damage" and trigger_row.damage_type:
            trigger_name = f"on_{trigger_row.damage_type.lower()}_damage"
        else:
            trigger_name = f"on_{_slugify(trigger_row.trigger_type)}"

        conditions = []
        if trigger_row.weapon_requirement:
            conditions.append(
                f"weapon_requirement:{trigger_row.weapon_requirement}"
            )
        if trigger_row.condition:
            conditions.append(trigger_row.condition)

        return SupportEffectTrigger(
            trigger=trigger_name,
            condition="; ".join(conditions) if conditions else None,
        )

    def _interaction_effect(
        self,
        record: CombatEffectRecord,
        interaction: CombatEffectInteractionRecord,
    ) -> SupportEffect | None:
        target_type = self.SCOPE_TARGET_TYPES.get(interaction.scope)

        if target_type is None:
            # An unsupported/ambiguous scope - do not guess which of
            # self/ally/group/enemy this reaches.
            return None

        category = (
            SupportEffectCategory.DEBUFF
            if target_type == SupportTargetType.ENEMY
            else SupportEffectCategory.BUFF
        )

        unit = (
            EffectUnit.PERCENT
            if interaction.unit == "percent"
            else EffectUnit.FLAT
        )

        resistance_reduction = (
            interaction.value if interaction.unit == "resistance" else None
        )

        conditions = (
            (interaction.condition,) if interaction.condition else ()
        )

        trigger = SupportEffectTrigger(
            trigger=f"on_{_slugify(record.name)}_active",
            condition=interaction.condition,
        )

        requires_status = (
            record.name if record.category == "Status" else None
        )

        return SupportEffect(
            source=record.name,
            name=interaction.target_name,
            category=category,
            effect_type=_slugify(interaction.target_name),
            target_type=target_type,
            magnitude=interaction.value if interaction.value is not None else 0.0,
            unit=unit,
            duration=interaction.duration,
            conditions=conditions,
            trigger=trigger,
            resistance_reduction=resistance_reduction,
            requires_status=requires_status,
        )
