import pytest

from minmax.base_character_state import BaseCharacterState
from minmax.resource_costs import ResourceType
from minmax.resource_state import StaticResourcePool, StaticResourceState


def _base_state() -> BaseCharacterState:
    return BaseCharacterState(
        max_health=20_000,
        max_magicka=30_000,
        max_stamina=18_000,
        health_recovery=500,
        magicka_recovery=1_700,
        stamina_recovery=900,
        traces={},
    )


def test_static_resource_state_adapts_base_character_state_without_recalculation():
    state = StaticResourceState.from_base_character_state(_base_state())

    assert state.health.resource is ResourceType.HEALTH
    assert state.health.maximum == 20_000
    assert state.health.displayed_recovery == 500

    assert state.magicka.resource is ResourceType.MAGICKA
    assert state.magicka.maximum == 30_000
    assert state.magicka.displayed_recovery == 1_700

    assert state.stamina.resource is ResourceType.STAMINA
    assert state.stamina.maximum == 18_000
    assert state.stamina.displayed_recovery == 900


def test_static_resource_state_resolves_primary_pool_by_resource():
    state = StaticResourceState.from_base_character_state(_base_state())

    assert state.pool(ResourceType.HEALTH) is state.health
    assert state.pool(ResourceType.MAGICKA) is state.magicka
    assert state.pool(ResourceType.STAMINA) is state.stamina


def test_static_resource_state_does_not_invent_ultimate_static_pool():
    state = StaticResourceState.from_base_character_state(_base_state())

    with pytest.raises(ValueError, match="No static primary resource pool"):
        state.pool(ResourceType.ULTIMATE)


def test_static_resource_pool_rejects_ultimate_and_negative_values():
    with pytest.raises(ValueError, match="Ultimate is not a primary static resource pool"):
        StaticResourcePool(ResourceType.ULTIMATE, maximum=500, displayed_recovery=0)

    with pytest.raises(ValueError, match="maximum cannot be negative"):
        StaticResourcePool(ResourceType.MAGICKA, maximum=-1, displayed_recovery=0)

    with pytest.raises(ValueError, match="recovery cannot be negative"):
        StaticResourcePool(ResourceType.STAMINA, maximum=12_000, displayed_recovery=-1)
