from __future__ import annotations

from types import SimpleNamespace

from services.extreme_conditional_actual_heal_objective_optimization_service import (
    ExtremeConditionalActualHealObjectiveOptimizationService,
    ExtremeConditionalHealingObjectiveEventResult,
)
from services.extreme_healing_event_service import ExtremeHealingEventResult
from services.extreme_sorcerer_blood_magic_healing_event_service import (
    ExtremeSorcererBloodMagicHealingEventResult,
)


def _selected(*, critical_heal: float) -> ExtremeHealingEventResult:
    return ExtremeHealingEventResult(
        entity_id="combat_prayer",
        normal_heal=critical_heal / 1.5,
        critical_heal=critical_heal,
        critical_healing_bonus=0.0,
        critical_multiplier=1.5,
        heal_coefficient_numbers=(1,),
        crit_eligible_coefficient_numbers=(1,),
        noncrit_coefficient_numbers=(),
        tooltip_result=SimpleNamespace(),
        unresolved=(),
    )


def _blood_magic(*, critical_heal: float) -> ExtremeSorcererBloodMagicHealingEventResult:
    return ExtremeSorcererBloodMagicHealingEventResult(
        normal_event=SimpleNamespace(
            source="Sorcerer: Blood Magic",
            target="self",
            amount=critical_heal / 1.5,
            time_seconds=3.0,
        ),
        normal_heal=critical_heal / 1.5,
        critical_heal=critical_heal,
        critical_healing_bonus=0.0,
        critical_multiplier=1.5,
        unresolved=(),
    )


def test_selected_heal_wins_without_rewriting_selected_event() -> None:
    wrapped = ExtremeConditionalActualHealObjectiveOptimizationService._wrap_selected_event(
        _selected(critical_heal=9000.0),
        blood_magic_event=_blood_magic(critical_heal=7000.0),
    )

    assert isinstance(wrapped, ExtremeConditionalHealingObjectiveEventResult)
    assert wrapped.entity_id == "combat_prayer"
    assert wrapped.critical_heal == 9000.0
    assert wrapped.objective_critical_heal == 9000.0
    assert wrapped.objective_source == "combat_prayer"
    assert wrapped.objective_target == "selected_heal_recipient"
    assert wrapped.blood_magic_event is not None
    assert wrapped.blood_magic_event.normal_event.target == "self"


def test_blood_magic_can_win_as_distinct_self_heal_event() -> None:
    wrapped = ExtremeConditionalActualHealObjectiveOptimizationService._wrap_selected_event(
        _selected(critical_heal=9000.0),
        blood_magic_event=_blood_magic(critical_heal=12000.0),
    )

    assert wrapped.critical_heal == 9000.0
    assert wrapped.objective_critical_heal == 12000.0
    assert wrapped.objective_source == "Sorcerer: Blood Magic"
    assert wrapped.objective_target == "self"
    assert ExtremeConditionalActualHealObjectiveOptimizationService._score(wrapped) == 12000.0


def test_objective_ranking_never_sums_separate_recipient_events() -> None:
    wrapped = ExtremeConditionalActualHealObjectiveOptimizationService._wrap_selected_event(
        _selected(critical_heal=9000.0),
        blood_magic_event=_blood_magic(critical_heal=12000.0),
    )

    assert wrapped.objective_critical_heal == 12000.0
    assert wrapped.objective_critical_heal != 21000.0


def test_plain_healing_event_score_keeps_legacy_selected_event_semantics() -> None:
    selected = _selected(critical_heal=9000.0)

    assert ExtremeConditionalActualHealObjectiveOptimizationService._score(selected) == 9000.0
