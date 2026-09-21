from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from minmax.character_progression import AttributeAllocation
from models.build_model import PlayerBuild
from services.extreme_canonical_actual_heal_optimization_service import (
    ExtremeCanonicalActualHealOptimizationService,
)


@dataclass(frozen=True)
class _Progression:
    attributes: AttributeAllocation = AttributeAllocation()


class _ConditionService:
    def resolve(self, build, *, active_bar="front"):
        return SimpleNamespace(
            condition_context=frozenset({"food_buff_active"}),
            unresolved=("condition note",),
        )


class _ConditionedFactory:
    def __init__(self):
        self.received = None

    def build(self, **kwargs):
        self.received = kwargs
        return SimpleNamespace(unresolved_gear_effects=("gear note",))


class _HealingEvents:
    def evaluate(self, *, build, context, entity_id):
        return SimpleNamespace(entity_id=entity_id, unresolved=("event note",))


def test_canonical_h1_evaluation_passes_explicit_gear_condition_context() -> None:
    service = ExtremeCanonicalActualHealOptimizationService.__new__(
        ExtremeCanonicalActualHealOptimizationService
    )
    service.build_condition_context = _ConditionService()
    service.candidate_gear_conditions = None
    service.conditioned_context_factory = _ConditionedFactory()
    service.healing_events = _HealingEvents()

    build = PlayerBuild(AttributeMagicka=64)
    event, unresolved = service._evaluate(
        build,
        progression=_Progression(),
        character_id="char",
        build_id="build",
        entity_id="heal",
        active_bar="front",
    )

    assert event.entity_id == "heal"
    assert service.conditioned_context_factory.received["gear_condition_context"] == frozenset(
        {"food_buff_active"}
    )
    assert service.conditioned_context_factory.received["progression"].attributes == AttributeAllocation(
        health=0,
        magicka=64,
        stamina=0,
    )
    assert unresolved == ("gear note", "event note", "condition note")
