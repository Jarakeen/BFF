from types import SimpleNamespace

from tools.audit_phase13_staff_heavy_restore_cap_clipping import (
    _cap_status,
    _reported_post_event_pool_state,
)


def _event(*, max_resource_amount, source_resources):
    return SimpleNamespace(
        max_resource_amount=max_resource_amount,
        raw_event={
            "maxResourceAmount": max_resource_amount,
            "sourceResources": source_resources,
        },
    )


def test_reported_post_event_pool_state_detects_at_cap_without_resource_type_mapping():
    event = _event(
        max_resource_amount=34643,
        source_resources={
            "magicka": 34643,
            "maxMagicka": 34643,
            "stamina": 12000,
            "maxStamina": 15894,
            "ultimate": 250,
            "maxUltimate": 500,
        },
    )

    assert _reported_post_event_pool_state(event) == {
        "resource": "magicka",
        "current": 34643.0,
        "maximum": 34643.0,
        "at_cap": True,
    }
    assert _cap_status(event) == "at_reported_cap"


def test_reported_post_event_pool_state_detects_below_cap():
    event = _event(
        max_resource_amount=34643,
        source_resources={
            "magicka": 25212,
            "maxMagicka": 34643,
            "stamina": 15894,
            "maxStamina": 15894,
        },
    )

    state = _reported_post_event_pool_state(event)
    assert state is not None
    assert state["resource"] == "magicka"
    assert state["at_cap"] is False
    assert _cap_status(event) == "below_reported_cap"


def test_reported_post_event_pool_state_fails_closed_when_max_pool_is_ambiguous():
    event = _event(
        max_resource_amount=500,
        source_resources={
            "ultimate": 500,
            "maxUltimate": 500,
            "werewolf": 500,
            "maxWerewolf": 500,
        },
    )

    assert _reported_post_event_pool_state(event) is None
    assert _cap_status(event) == "unresolved"
