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


class ExtremeDragonBloodSkillComponentRepository:
    """Overlay reviewed U50 Dragon Blood HEAL component identity without DB writes.

    The local canonical database currently contains coefficient math and
    coefficient-aware tooltip wording for the U50 Dragon Blood family, but does
    not yet persist HEAL classification for these concrete max-rank rows. This
    repository delegates every unrelated lookup to the ordinary component
    repository and overlays only the exact skill-rank/coefficient pairs proven by
    the reviewed U50 corpus.

    The mapping is intentionally numeric at the concrete rank boundary because
    these ``skill_rank_id`` values are the rows whose coefficient placeholders
    were audited. It is not a cross-update logical identity. If a later update
    changes the rank rows, this overlay must not silently follow them.

    ``Blood of the Green Dragon`` coefficient #2 is a five-second healing-over-
    time total in the tooltip corpus. Its recipient and periodic scope are proven,
    but it deliberately receives no ``heal_event_key`` because one coefficient
    total must not be mistaken for one actual tick. The canonical event layer
    therefore keeps that morph unresolved until tick identity is proven.
    """

    DRAGON_BLOOD_RANK_ID = 5397
    GREEN_DRAGON_BLOOD_RANK_ID = 5398
    ELDER_DRAGON_BLOOD_RANK_ID = 5399

    _REVIEWED: dict[tuple[int, int], SkillComponentClassification] = {
        (DRAGON_BLOOD_RANK_ID, 1): SkillComponentClassification(
            skill_rank_id=DRAGON_BLOOD_RANK_ID,
            coefficient_number=1,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=False,
            is_aoe=False,
            can_crit=True,
            source="reviewed U50 Dragon Blood coefficient-local tooltip + official critical-heal patch history",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.SELF,
            heal_temporal_scope=HealTemporalScope.DIRECT,
            heal_recipient_key="caster",
            heal_event_key="cast_direct",
        ),
        (GREEN_DRAGON_BLOOD_RANK_ID, 1): SkillComponentClassification(
            skill_rank_id=GREEN_DRAGON_BLOOD_RANK_ID,
            coefficient_number=1,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=False,
            is_aoe=False,
            can_crit=True,
            source="reviewed U50 Blood of the Green Dragon coefficient-local tooltip + official critical-heal patch history",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.SELF,
            heal_temporal_scope=HealTemporalScope.DIRECT,
            heal_recipient_key="caster",
            heal_event_key="cast_direct",
        ),
        (GREEN_DRAGON_BLOOD_RANK_ID, 2): SkillComponentClassification(
            skill_rank_id=GREEN_DRAGON_BLOOD_RANK_ID,
            coefficient_number=2,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=True,
            is_aoe=False,
            can_crit=True,
            source="reviewed U50 Blood of the Green Dragon five-second healing-over-time tooltip + official critical-heal patch history",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.SELF,
            heal_temporal_scope=HealTemporalScope.PERIODIC,
            heal_recipient_key="caster",
            heal_event_key=None,
        ),
        (ELDER_DRAGON_BLOOD_RANK_ID, 1): SkillComponentClassification(
            skill_rank_id=ELDER_DRAGON_BLOOD_RANK_ID,
            coefficient_number=1,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=False,
            is_aoe=False,
            can_crit=True,
            source="reviewed U50 Blood of the Elder Dragon coefficient-local self-heal wording + official critical-heal patch history",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.SELF,
            heal_temporal_scope=HealTemporalScope.DIRECT,
            heal_recipient_key="caster",
            heal_event_key="cast_direct",
        ),
        (ELDER_DRAGON_BLOOD_RANK_ID, 2): SkillComponentClassification(
            skill_rank_id=ELDER_DRAGON_BLOOD_RANK_ID,
            coefficient_number=2,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=False,
            is_aoe=True,
            can_crit=True,
            source="reviewed U50 Blood of the Elder Dragon coefficient-local nearby-allies wording + official critical-heal patch history",
            confidence=1.0,
            heal_recipient_scope=HealRecipientScope.GROUP,
            heal_temporal_scope=HealTemporalScope.DIRECT,
            heal_recipient_key="nearby_allies",
            heal_event_key="cast_direct",
        ),
    }

    def __init__(
        self,
        database_path: str | Path,
        *,
        base_repository: SkillComponentRepository | None = None,
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
