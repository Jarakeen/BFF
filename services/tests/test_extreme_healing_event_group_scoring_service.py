from __future__ import annotations

import pytest

from minmax.skill_component_classification import (
    HealRecipientScope,
    HealTemporalScope,
    SkillComponentClassification,
    SkillEffectKind,
)
from services.extreme_healing_event_group_scoring_service import (
    ExtremeHealingEventGroupScoringService,
)


def _heal(
    number: int,
    *,
    can_crit: bool | None = True,
    recipient_key: str = "target_1",
    event_key: str = "cast_1",
    recipient_scope=HealRecipientScope.ALLY,
    temporal_scope=HealTemporalScope.DIRECT,
):
    return SkillComponentClassification(
        skill_rank_id=42,
        coefficient_number=number,
        effect_kind=SkillEffectKind.HEAL,
        can_crit=can_crit,
        heal_recipient_scope=recipient_scope,
        heal_temporal_scope=temporal_scope,
        heal_recipient_key=recipient_key,
        heal_event_key=event_key,
    )


def test_same_event_coefficients_sum_before_comparing_against_other_events():
    result = ExtremeHealingEventGroupScoringService().score(
        components=(
            _heal(1),
            _heal(2),
            _heal(3, recipient_key="target_2"),
        ),
        value_by_coefficient={1: 600.0, 2: 500.0, 3: 1000.0},
        critical_multiplier=1.5,
    )

    assert result.complete
    assert result.largest_normal_heal == pytest.approx(1100.0)
    assert result.largest_critical_heal == pytest.approx(1650.0)
    assert result.normal_winner_coefficients == (1, 2)
    assert result.critical_winner_coefficients == (1, 2)


def test_distinct_recipients_are_compared_not_summed():
    result = ExtremeHealingEventGroupScoringService().score(
        components=(
            _heal(
                1,
                recipient_key="self",
                recipient_scope=HealRecipientScope.SELF,
            ),
            _heal(2, recipient_key="nearby_ally"),
        ),
        value_by_coefficient={1: 1000.0, 2: 700.0},
        critical_multiplier=1.5,
    )

    assert result.largest_normal_heal == pytest.approx(1000.0)
    assert result.largest_critical_heal == pytest.approx(1500.0)
    assert result.normal_winner_coefficients == (1,)
    assert result.critical_winner_coefficients == (1,)


def test_direct_and_periodic_events_are_compared_not_summed():
    result = ExtremeHealingEventGroupScoringService().score(
        components=(
            _heal(1, event_key="direct"),
            _heal(
                2,
                event_key="hot_tick",
                temporal_scope=HealTemporalScope.PERIODIC,
            ),
        ),
        value_by_coefficient={1: 900.0, 2: 650.0},
        critical_multiplier=1.5,
    )

    assert result.largest_normal_heal == pytest.approx(900.0)
    assert result.largest_critical_heal == pytest.approx(1350.0)
    assert result.normal_winner_coefficients == (1,)


def test_noncrittable_component_stays_normal_inside_a_mixed_event():
    result = ExtremeHealingEventGroupScoringService().score(
        components=(
            _heal(1, can_crit=True),
            _heal(2, can_crit=False),
        ),
        value_by_coefficient={1: 1000.0, 2: 300.0},
        critical_multiplier=1.5,
    )

    assert result.largest_normal_heal == pytest.approx(1300.0)
    assert result.largest_critical_heal == pytest.approx(1800.0)


def test_unknown_critical_eligibility_keeps_normal_score_but_blocks_complete_result():
    result = ExtremeHealingEventGroupScoringService().score(
        components=(_heal(1, can_crit=None),),
        value_by_coefficient={1: 1000.0},
        critical_multiplier=1.5,
    )

    assert result.largest_normal_heal == pytest.approx(1000.0)
    assert result.largest_critical_heal is None
    assert result.normal_winner_coefficients == (1,)
    assert result.critical_winner_coefficients == ()
    assert any("critical eligibility unresolved" in message for message in result.unresolved)
    assert not result.complete


def test_missing_component_value_is_explicit_not_zero():
    result = ExtremeHealingEventGroupScoringService().score(
        components=(_heal(1),),
        value_by_coefficient={},
        critical_multiplier=1.5,
    )

    assert result.largest_normal_heal is None
    assert result.largest_critical_heal is None
    assert result.unresolved == (
        "HEAL coefficient values unavailable for event group: 1",
    )
