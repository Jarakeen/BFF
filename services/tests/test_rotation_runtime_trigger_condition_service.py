import pytest

from services.rotation_runtime_trigger_condition_service import (
    RotationRuntimeTriggerConditionService,
    RotationRuntimeTriggerObservation,
)
from services.rotation_runtime_triggered_intent_service import RotationRuntimeTriggeredIntent


def _intent() -> RotationRuntimeTriggeredIntent:
    return RotationRuntimeTriggeredIntent(
        intent_id="xalvakka:pack_encounter_adds:iron_atronach",
        trigger_key="encounter_actor_active:iron_atronach",
        directive="acquire_and_maintain_owned_add_when_active",
        source_plan_id="performance-mode-rg",
        source_seat_id="off-tank",
        encounter_id="xalvakka",
        target_key="Iron Atronach",
        required_capability_type="taunt",
        source="reviewed Tank add activity",
    )


def _observation(**changes) -> RotationRuntimeTriggerObservation:
    values = dict(
        trigger_key="encounter_actor_active:iron_atronach",
        observed_at_seconds=37.25,
        source="authoritative runtime actor-activity observer",
        encounter_id="xalvakka",
        source_plan_id="performance-mode-rg",
        source_seat_id="off-tank",
        authoritative=True,
    )
    values.update(changes)
    return RotationRuntimeTriggerObservation(**values)


def test_authoritative_matching_observation_activates_intent_at_observed_time() -> None:
    intent = _intent()
    result = RotationRuntimeTriggerConditionService().resolve(
        intents=(intent,),
        observations=(_observation(),),
    )

    assert result.pending == ()
    assert result.rejected_observations == ()
    assert len(result.activated) == 1
    activated = result.activated[0]
    assert activated.intent is intent
    assert activated.activated_at_seconds == pytest.approx(37.25)
    assert activated.trigger_source == "authoritative runtime actor-activity observer"
    assert not hasattr(activated, "time_seconds")
    assert not hasattr(activated, "action_name")
    assert not hasattr(activated, "bar")


def test_non_authoritative_observation_does_not_activate_intent() -> None:
    intent = _intent()
    result = RotationRuntimeTriggerConditionService().resolve(
        intents=(intent,),
        observations=(_observation(authoritative=False),),
    )

    assert result.activated == ()
    assert result.pending == (intent,)
    assert result.rejected_observations == (
        "encounter_actor_active:iron_atronach: observation is not authoritative runtime evidence",
    )


def test_wrong_scope_observation_fails_closed() -> None:
    intent = _intent()
    result = RotationRuntimeTriggerConditionService().resolve(
        intents=(intent,),
        observations=(_observation(source_seat_id="main-tank"),),
    )

    assert result.activated == ()
    assert result.pending == (intent,)
    assert result.rejected_observations == (
        "encounter_actor_active:iron_atronach: authoritative observation seat scope does not match pending runtime intent",
    )


def test_missing_observation_leaves_intent_pending_without_guessing_time() -> None:
    intent = _intent()
    result = RotationRuntimeTriggerConditionService().resolve(
        intents=(intent,),
        observations=(),
    )

    assert result.activated == ()
    assert result.pending == (intent,)
    assert result.rejected_observations == ()


def test_earliest_authoritative_matching_observation_wins() -> None:
    intent = _intent()
    result = RotationRuntimeTriggerConditionService().resolve(
        intents=(intent,),
        observations=(
            _observation(observed_at_seconds=39.0, source="later observer event"),
            _observation(observed_at_seconds=37.25, source="first authoritative observer event"),
        ),
    )

    assert len(result.activated) == 1
    assert result.activated[0].activated_at_seconds == pytest.approx(37.25)
    assert result.activated[0].trigger_source == "first authoritative observer event"


def test_observation_time_must_be_real_runtime_time() -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        _observation(observed_at_seconds=float("nan"))
