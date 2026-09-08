from __future__ import annotations

from minmax.skill_component_classification import (
    HealRecipientScope,
    HealTemporalScope,
    SkillComponentClassification,
    SkillEffectKind,
)
from services.extreme_healing_component_identity_service import (
    ExtremeHealingComponentIdentityService,
)


def _heal(
    number: int,
    *,
    recipient_scope=HealRecipientScope.ALLY,
    temporal_scope=HealTemporalScope.DIRECT,
    recipient_key: str | None = "target_1",
    event_key: str | None = "cast_1",
):
    return SkillComponentClassification(
        skill_rank_id=42,
        coefficient_number=number,
        effect_kind=SkillEffectKind.HEAL,
        can_crit=True,
        heal_recipient_scope=recipient_scope,
        heal_temporal_scope=temporal_scope,
        heal_recipient_key=recipient_key,
        heal_event_key=event_key,
    )


def test_groups_coefficients_only_when_recipient_and_event_identity_match():
    result = ExtremeHealingComponentIdentityService().resolve(
        (
            _heal(1),
            _heal(2),
            _heal(3, recipient_key="target_2"),
            _heal(4, event_key="tick_1", temporal_scope=HealTemporalScope.PERIODIC),
        )
    )

    assert result.complete
    assert result.unresolved == ()
    assert tuple(group.coefficient_numbers for group in result.groups) == (
        (1, 2),
        (4,),
        (3,),
    )


def test_distinct_recipients_remain_distinct_even_at_same_time():
    result = ExtremeHealingComponentIdentityService().resolve(
        (
            _heal(1, recipient_scope=HealRecipientScope.SELF, recipient_key="self"),
            _heal(2, recipient_scope=HealRecipientScope.ALLY, recipient_key="nearby_ally"),
        )
    )

    assert result.complete
    assert {group.coefficient_numbers for group in result.groups} == {(1,), (2,)}


def test_direct_and_periodic_heals_remain_distinct_for_same_recipient():
    result = ExtremeHealingComponentIdentityService().resolve(
        (
            _heal(1, event_key="direct"),
            _heal(
                2,
                temporal_scope=HealTemporalScope.PERIODIC,
                event_key="hot_tick",
            ),
        )
    )

    assert result.complete
    assert {group.coefficient_numbers for group in result.groups} == {(1,), (2,)}


def test_missing_reviewed_identity_blocks_complete_grouping_instead_of_guessing():
    result = ExtremeHealingComponentIdentityService().resolve(
        (
            _heal(1),
            _heal(2, event_key=None),
        )
    )

    assert not result.complete
    assert result.groups == ()
    assert result.unresolved == (
        "HEAL component event identity is unresolved for coefficient(s): 2",
    )


def test_non_heal_components_do_not_need_heal_event_identity():
    damage = SkillComponentClassification(
        skill_rank_id=42,
        coefficient_number=9,
        effect_kind=SkillEffectKind.DAMAGE,
        can_crit=True,
    )
    result = ExtremeHealingComponentIdentityService().resolve((damage, _heal(1)))

    assert result.complete
    assert len(result.groups) == 1
    assert result.groups[0].coefficient_numbers == (1,)
