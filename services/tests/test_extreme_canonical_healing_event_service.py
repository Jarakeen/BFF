from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.skill_component_classification import (
    HealRecipientScope,
    HealTemporalScope,
    SkillComponentClassification,
    SkillEffectKind,
)
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_canonical_healing_event_service import (
    ExtremeCanonicalHealingEventService,
    _CanonicalIdentityRecipientScope,
)


class _FakeComponents:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def get_for_skill_rank(self, _skill_rank_id):
        return self.rows


class _FakeTooltipService:
    def __init__(self, result, rows):
        self.result = result
        self.components = _FakeComponents(rows)

    def evaluate_entity_id(self, **_kwargs):
        return self.result


def _context():
    return SimpleNamespace(
        core_state=SimpleNamespace(
            derived={
                StatId.CRITICAL_HEALING: SimpleNamespace(final_value=0.20),
            }
        ),
        progression=None,
        active_bar="front",
    )


def _result(skill_name):
    return SimpleNamespace(
        skill=SimpleNamespace(skill_rank_id=42, name=skill_name),
        components=(
            SimpleNamespace(coefficient_number=1, final_value=1000.0),
            SimpleNamespace(coefficient_number=2, final_value=700.0),
        ),
        component_actual_effect_trace=(),
        unresolved=(),
    )


def _component(
    number,
    *,
    recipient_scope=None,
    temporal_scope=None,
    recipient_key=None,
    event_key=None,
    can_crit=True,
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


def _service(skill_name, rows):
    return ExtremeCanonicalHealingEventService(
        tooltip_service=_FakeTooltipService(_result(skill_name), rows)
    )


def test_canonical_recipient_adapter_accepts_base_recipient_proof_inputs():
    result = _CanonicalIdentityRecipientScope().resolve(
        ability_name="Reviewed Composite Heal",
        heal_coefficient_numbers=(1, 2),
        coefficient_traces=(SimpleNamespace(coefficient_number=1),),
    )

    assert result.single_recipient_safe
    assert not result.recipient_selection_required
    assert result.selected_coefficient_numbers is None
    assert result.unresolved == ()


def test_canonical_identity_scores_different_recipients_as_independent_events():
    service = _service(
        "Reviewed Split Heal",
        (
            _component(
                1,
                recipient_scope=HealRecipientScope.SELF,
                temporal_scope=HealTemporalScope.DIRECT,
                recipient_key="caster",
                event_key="cast/direct",
            ),
            _component(
                2,
                recipient_scope=HealRecipientScope.ALLY,
                temporal_scope=HealTemporalScope.DIRECT,
                recipient_key="nearby ally",
                event_key="cast/direct",
            ),
        ),
    )

    result = service.evaluate(
        build=PlayerBuild(BuildName="Split"),
        context=_context(),
        entity_id="reviewed_split_heal",
    )

    assert result.normal_heal == pytest.approx(1000.0)
    assert result.critical_heal == pytest.approx(1700.0)
    assert result.unresolved == ()
    assert result.mechanic_complete


def test_canonical_identity_scores_direct_and_periodic_heals_independently():
    service = _service(
        "Reviewed Direct Plus HoT",
        (
            _component(
                1,
                recipient_scope=HealRecipientScope.SELF,
                temporal_scope=HealTemporalScope.DIRECT,
                recipient_key="caster",
                event_key="direct",
            ),
            _component(
                2,
                recipient_scope=HealRecipientScope.SELF,
                temporal_scope=HealTemporalScope.PERIODIC,
                recipient_key="caster",
                event_key="hot/tick",
            ),
        ),
    )

    result = service.evaluate(
        build=PlayerBuild(BuildName="Timed"),
        context=_context(),
        entity_id="reviewed_direct_plus_hot",
    )

    assert result.normal_heal == pytest.approx(1000.0)
    assert result.critical_heal == pytest.approx(1700.0)
    assert result.unresolved == ()


def test_canonical_identity_still_sums_coefficients_proven_to_share_one_event():
    service = _service(
        "Reviewed Composite Heal",
        (
            _component(
                1,
                recipient_scope=HealRecipientScope.ALLY,
                temporal_scope=HealTemporalScope.DIRECT,
                recipient_key="selected ally",
                event_key="direct",
            ),
            _component(
                2,
                recipient_scope=HealRecipientScope.ALLY,
                temporal_scope=HealTemporalScope.DIRECT,
                recipient_key="selected ally",
                event_key="direct",
            ),
        ),
    )

    result = service.evaluate(
        build=PlayerBuild(BuildName="Composite"),
        context=_context(),
        entity_id="reviewed_composite_heal",
    )

    assert result.normal_heal == pytest.approx(1700.0)
    assert result.critical_heal == pytest.approx(2890.0)
    assert result.unresolved == ()


def test_pet_special_activation_keeps_numeric_score_but_requires_runtime_pet_proof():
    service = _service(
        "Summon Twilight Matriarch",
        (
            _component(
                1,
                recipient_scope=HealRecipientScope.GROUP,
                temporal_scope=HealTemporalScope.DIRECT,
                recipient_key="friendly_targets",
                event_key="pet_special_activation",
            ),
            _component(
                2,
                recipient_scope=HealRecipientScope.PET,
                temporal_scope=HealTemporalScope.DIRECT,
                recipient_key="summoned_pet",
                event_key="pet_special_activation",
            ),
        ),
    )

    result = service.evaluate(
        build=PlayerBuild(BuildName="Pet"),
        context=_context(),
        entity_id="summon_twilight_matriarch",
    )

    assert result.normal_heal == pytest.approx(1000.0)
    assert result.critical_heal == pytest.approx(1700.0)
    assert ExtremeCanonicalHealingEventService.PET_SPECIAL_ACTIVATION_UNRESOLVED in result.unresolved
    assert not result.mechanic_complete


def test_larger_pet_component_cannot_win_player_recipient_objective():
    rows = (
        _component(
            1,
            recipient_scope=HealRecipientScope.GROUP,
            temporal_scope=HealTemporalScope.DIRECT,
            recipient_key="friendly_targets",
            event_key="pet_special_activation",
        ),
        _component(
            2,
            recipient_scope=HealRecipientScope.PET,
            temporal_scope=HealTemporalScope.DIRECT,
            recipient_key="summoned_pet",
            event_key="pet_special_activation",
        ),
    )
    result = SimpleNamespace(
        skill=SimpleNamespace(skill_rank_id=42, name="Summon Twilight Matriarch"),
        components=(
            SimpleNamespace(coefficient_number=1, final_value=1000.0),
            SimpleNamespace(coefficient_number=2, final_value=5000.0),
        ),
        component_actual_effect_trace=(),
        unresolved=(),
    )
    service = ExtremeCanonicalHealingEventService(
        tooltip_service=_FakeTooltipService(result, rows)
    )

    evaluated = service.evaluate(
        build=PlayerBuild(BuildName="Pet"),
        context=_context(),
        entity_id="summon_twilight_matriarch",
    )

    assert evaluated.normal_heal == pytest.approx(1000.0)
    assert evaluated.critical_heal == pytest.approx(1700.0)
    assert ExtremeCanonicalHealingEventService.PET_SPECIAL_ACTIVATION_UNRESOLVED in evaluated.unresolved


def test_missing_identity_preserves_legacy_multi_recipient_guard():
    service = _service(
        "Blood of the Elder Dragon",
        (_component(1), _component(2)),
    )

    result = service.evaluate(
        build=PlayerBuild(BuildName="DK"),
        context=_context(),
        entity_id="blood_of_the_elder_dragon",
    )

    assert result.normal_heal is None
    assert result.critical_heal is None
    assert any("one-recipient Extreme heal is unresolved" in message for message in result.unresolved)
    assert not result.mechanic_complete


def test_missing_identity_preserves_legacy_multi_time_guard():
    service = _service(
        "Blood of the Green Dragon",
        (_component(1), _component(2)),
    )

    result = service.evaluate(
        build=PlayerBuild(BuildName="DK"),
        context=_context(),
        entity_id="blood_of_the_green_dragon",
    )

    assert result.normal_heal is None
    assert result.critical_heal is None
    assert any("one-event Extreme heal is unresolved" in message for message in result.unresolved)
    assert not result.mechanic_complete
