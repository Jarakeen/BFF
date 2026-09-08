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


class ExtremeSorcererSkillComponentRepository:
    """Overlay reviewed U50 Sorcerer coefficient-local healing identity.

    The local canonical database contains coefficient math and coefficient-aware
    tooltip wording for several Sorcerer pet and ward heals, but these rows are
    not yet persisted as HEAL classifications. This repository overlays only the
    exact max-rank skill-rank/coefficient pairs proven by the read-only U50 audit.

    Crit eligibility is deliberately left unresolved because the local corpus
    proves recipient/event identity but does not prove whether these concrete
    heal components can critically heal. The canonical event scorer may therefore
    compute a normal heal while retaining an explicit critical-heal blocker.

    Dark Exchange-family and Surge-family skills are not included because the
    local canonical rows expose no coefficient math for their healing. They remain
    trigger/runtime mechanics until a separate evidence path proves their event
    values and activation conditions.
    """

    WINGED_TWILIGHT_RANK_ID = 4845
    TWILIGHT_MATRIARCH_RANK_ID = 4847
    UNSTABLE_CLANNFEAR_RANK_ID = 4750
    REGENERATIVE_WARD_RANK_ID = 5123

    _REVIEWED: dict[tuple[int, int], SkillComponentClassification] = {
        (WINGED_TWILIGHT_RANK_ID, 3): SkillComponentClassification(
            skill_rank_id=WINGED_TWILIGHT_RANK_ID,
            coefficient_number=3,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=False,
            is_aoe=False,
            can_crit=None,
            source="reviewed U50 Winged Twilight coefficient-local friendly-target heal wording",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.ALLY,
            heal_temporal_scope=HealTemporalScope.DIRECT,
            heal_recipient_key="friendly_target",
            heal_event_key="pet_special_activation",
        ),
        (WINGED_TWILIGHT_RANK_ID, 4): SkillComponentClassification(
            skill_rank_id=WINGED_TWILIGHT_RANK_ID,
            coefficient_number=4,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=False,
            is_aoe=False,
            can_crit=None,
            source="reviewed U50 Winged Twilight coefficient-local pet-self heal wording",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.PET,
            heal_temporal_scope=HealTemporalScope.DIRECT,
            heal_recipient_key="summoned_pet",
            heal_event_key="pet_special_activation",
        ),
        (TWILIGHT_MATRIARCH_RANK_ID, 3): SkillComponentClassification(
            skill_rank_id=TWILIGHT_MATRIARCH_RANK_ID,
            coefficient_number=3,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=False,
            is_aoe=True,
            can_crit=None,
            source="reviewed U50 Twilight Matriarch coefficient-local two-friendly-target heal wording",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.GROUP,
            heal_temporal_scope=HealTemporalScope.DIRECT,
            heal_recipient_key="friendly_targets",
            heal_event_key="pet_special_activation",
        ),
        (TWILIGHT_MATRIARCH_RANK_ID, 4): SkillComponentClassification(
            skill_rank_id=TWILIGHT_MATRIARCH_RANK_ID,
            coefficient_number=4,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=False,
            is_aoe=False,
            can_crit=None,
            source="reviewed U50 Twilight Matriarch coefficient-local pet-self heal wording",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.PET,
            heal_temporal_scope=HealTemporalScope.DIRECT,
            heal_recipient_key="summoned_pet",
            heal_event_key="pet_special_activation",
        ),
        (UNSTABLE_CLANNFEAR_RANK_ID, 3): SkillComponentClassification(
            skill_rank_id=UNSTABLE_CLANNFEAR_RANK_ID,
            coefficient_number=3,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=False,
            is_aoe=False,
            can_crit=None,
            source="reviewed U50 Unstable Clannfear coefficient-local player-self heal wording",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.SELF,
            heal_temporal_scope=HealTemporalScope.DIRECT,
            heal_recipient_key="caster",
            heal_event_key="pet_special_activation",
        ),
        (UNSTABLE_CLANNFEAR_RANK_ID, 4): SkillComponentClassification(
            skill_rank_id=UNSTABLE_CLANNFEAR_RANK_ID,
            coefficient_number=4,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=False,
            is_aoe=False,
            can_crit=None,
            source="reviewed U50 Unstable Clannfear coefficient-local pet-self heal wording",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.PET,
            heal_temporal_scope=HealTemporalScope.DIRECT,
            heal_recipient_key="summoned_pet",
            heal_event_key="pet_special_activation",
        ),
        (REGENERATIVE_WARD_RANK_ID, 2): SkillComponentClassification(
            skill_rank_id=REGENERATIVE_WARD_RANK_ID,
            coefficient_number=2,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=False,
            is_aoe=False,
            can_crit=None,
            source="reviewed U50 Regenerative Ward coefficient-local player-self heal wording",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.SELF,
            heal_temporal_scope=HealTemporalScope.DIRECT,
            heal_recipient_key="caster",
            heal_event_key="cast_direct",
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
