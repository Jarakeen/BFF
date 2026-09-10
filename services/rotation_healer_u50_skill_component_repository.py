from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from minmax.skill_component_classification import (
    HealRecipientScope,
    HealTemporalScope,
    SkillComponentClassification,
    SkillEffectKind,
)
from minmax.skill_component_repository import SkillComponentRepository


class RotationHealerU50SkillComponentRepository:
    """Overlay reviewed U50 healer component identity for rotation use.

    The local canonical database already contains coefficient-local tooltip
    wording and coefficient math for these concrete max-rank rows, but the
    persisted classification table does not yet expose their healer identity.
    This overlay adds only exact rank/coefficient identities reviewed from the
    U50 corpus.

    Synergy-owned healing components are intentionally excluded from this
    repository. They require a separate activation-owner/runtime contract and
    must not be scheduled as if the healer's cast automatically emitted them.
    ``is_intentionally_excluded_caster_healing_component`` exposes those exact
    reviewed exclusions so downstream caster-healing projection can distinguish
    them from genuinely missing classification evidence.

    Crit eligibility is left unresolved here unless separately proven. This
    repository owns healer identity and temporal scope, not critical-heal rules.
    """

    BUDDING_SEEDS_RANK_ID = 6910
    RADIATING_REGENERATION_RANK_ID = 5147
    COMBAT_PRAYER_RANK_ID = 6226
    ILLUSTRIOUS_HEALING_RANK_ID = 5110
    ENERGY_ORB_RANK_ID = 6328
    ECHOING_VIGOR_RANK_ID = 6640

    _INTENTIONALLY_EXCLUDED_CASTER_HEALING_COMPONENTS = frozenset(
        {
            # Harvest synergy is activated/owned by the synergy user, not emitted
            # automatically by the healer's Budding Seeds cast.
            (BUDDING_SEEDS_RANK_ID, 3),
            # Healing Combustion is the Energy Orb synergy consequence and likewise
            # requires separate activation-owner/runtime evidence.
            (ENERGY_ORB_RANK_ID, 2),
        }
    )

    _REVIEWED: dict[tuple[int, int], SkillComponentClassification] = {
        (BUDDING_SEEDS_RANK_ID, 1): SkillComponentClassification(
            skill_rank_id=BUDDING_SEEDS_RANK_ID,
            coefficient_number=1,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=False,
            is_aoe=True,
            can_crit=None,
            source="reviewed U50 Budding Seeds coefficient-local six-second bloom heal wording",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.GROUP,
            heal_temporal_scope=HealTemporalScope.DELAYED,
            heal_recipient_key="field_allies",
            heal_event_key="field_bloom",
        ),
        (BUDDING_SEEDS_RANK_ID, 2): SkillComponentClassification(
            skill_rank_id=BUDDING_SEEDS_RANK_ID,
            coefficient_number=2,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=True,
            is_aoe=True,
            can_crit=None,
            source="reviewed U50 Budding Seeds coefficient-local field heal every one second wording",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.GROUP,
            heal_temporal_scope=HealTemporalScope.PERIODIC,
            heal_recipient_key="field_allies",
            heal_event_key="field_periodic",
        ),
        (RADIATING_REGENERATION_RANK_ID, 1): SkillComponentClassification(
            skill_rank_id=RADIATING_REGENERATION_RANK_ID,
            coefficient_number=1,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=True,
            is_aoe=False,
            can_crit=None,
            source="reviewed U50 Radiating Regeneration coefficient-local heal over ten seconds wording",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.GROUP,
            heal_temporal_scope=HealTemporalScope.PERIODIC,
            heal_recipient_key="selected_nearby_allies",
            heal_event_key="regeneration_periodic",
        ),
        (COMBAT_PRAYER_RANK_ID, 1): SkillComponentClassification(
            skill_rank_id=COMBAT_PRAYER_RANK_ID,
            coefficient_number=1,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=False,
            is_aoe=True,
            can_crit=None,
            source="reviewed U50 Combat Prayer coefficient-local frontal ally heal wording",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.GROUP,
            heal_temporal_scope=HealTemporalScope.DIRECT,
            heal_recipient_key="frontal_allies",
            heal_event_key="cast_direct",
        ),
        (ILLUSTRIOUS_HEALING_RANK_ID, 1): SkillComponentClassification(
            skill_rank_id=ILLUSTRIOUS_HEALING_RANK_ID,
            coefficient_number=1,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=True,
            is_aoe=True,
            can_crit=None,
            source="reviewed U50 Illustrious Healing coefficient-local target-area heal over fifteen seconds wording",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.GROUP,
            heal_temporal_scope=HealTemporalScope.PERIODIC,
            heal_recipient_key="target_area_allies",
            heal_event_key="ground_periodic",
        ),
        (ENERGY_ORB_RANK_ID, 1): SkillComponentClassification(
            skill_rank_id=ENERGY_ORB_RANK_ID,
            coefficient_number=1,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=True,
            is_aoe=True,
            can_crit=None,
            source="reviewed U50 Energy Orb coefficient-local nearby ally heal every one second wording",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.GROUP,
            heal_temporal_scope=HealTemporalScope.PERIODIC,
            heal_recipient_key="orb_nearby_allies",
            heal_event_key="orb_periodic",
        ),
        (ECHOING_VIGOR_RANK_ID, 1): SkillComponentClassification(
            skill_rank_id=ECHOING_VIGOR_RANK_ID,
            coefficient_number=1,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=True,
            is_aoe=True,
            can_crit=None,
            source="reviewed U50 Echoing Vigor coefficient-local group heal over sixteen seconds wording",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.GROUP,
            heal_temporal_scope=HealTemporalScope.PERIODIC,
            heal_recipient_key="caster_and_allies",
            heal_event_key="vigor_periodic",
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

    @classmethod
    def is_intentionally_excluded_caster_healing_component(
        cls,
        *,
        skill_rank_id: int,
        coefficient_number: int,
    ) -> bool:
        """Return whether reviewed U50 evidence places this heal outside caster output."""
        return (
            int(skill_rank_id),
            int(coefficient_number),
        ) in cls._INTENTIONALLY_EXCLUDED_CASTER_HEALING_COMPONENTS

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
            is_dot=reviewed.is_dot,
            is_aoe=reviewed.is_aoe,
            can_crit=reviewed.can_crit,
            source=reviewed.source,
            confidence=reviewed.confidence,
            heal_recipient_scope=reviewed.heal_recipient_scope,
            heal_temporal_scope=reviewed.heal_temporal_scope,
            heal_recipient_key=reviewed.heal_recipient_key,
            heal_event_key=reviewed.heal_event_key,
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
