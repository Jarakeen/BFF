from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_classification import (
    HealTemporalScope,
    SkillComponentClassification,
    SkillEffectKind,
)
from models.build_model import PlayerBuild
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingService,
)


class _FakeCoefficients:
    def resolve_name(self, name):
        return SimpleNamespace(
            rank=SimpleNamespace(skill_rank_id=10, entity_id="heal_entity"),
            unresolved=(),
        )


class _FakeComponents:
    def __init__(self, classification):
        self.classification = classification

    def get_for_skill_rank(self, skill_rank_id):
        return (self.classification,)


class _FakeTooltipService:
    def __init__(self, classification):
        self.coefficients = _FakeCoefficients()
        self.components = _FakeComponents(classification)

    def evaluate_entity_id(self, *, build, context, entity_id):
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=10),
            components=(SimpleNamespace(coefficient_number=1, final_value=1000.0),),
            component_actual_effect_trace=(),
            unresolved=(),
        )


def _project(scope):
    classification = SkillComponentClassification(
        skill_rank_id=10,
        coefficient_number=1,
        effect_kind=SkillEffectKind.HEAL,
        is_dot=False,
        source="test",
        confidence=1.0,
        heal_temporal_scope=scope,
    )
    service = RotationHealerActionHealingService(
        ".",
        tooltip_service=_FakeTooltipService(classification),
    )
    plan = RotationPlan(
        character_name="Healer",
        build_name="Build",
        duration_seconds=10.0,
        actions=(
            RotationAction(
                time_seconds=2.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Heal",
                bar="front",
            ),
        ),
    )
    return service.project(plan=plan, build=PlayerBuild(), context=object())


def test_delayed_heal_becomes_runtime_seed_not_cast_time_heal():
    projection = _project(HealTemporalScope.DELAYED)

    assert projection.direct_events == ()
    assert projection.periodic_seeds == ()
    assert len(projection.delayed_seeds) == 1
    seed = projection.delayed_seeds[0]
    assert seed.time_seconds == 2.0
    assert seed.coefficient_number == 1
    assert seed.modeled_heal == 1000.0
    assert projection.unresolved == ()


def test_direct_scope_attaches_heal_to_cast_time():
    projection = _project(HealTemporalScope.DIRECT)

    assert len(projection.direct_events) == 1
    assert projection.direct_events[0].time_seconds == 2.0
    assert projection.periodic_seeds == ()
    assert projection.delayed_seeds == ()
    assert projection.unresolved == ()


def test_periodic_scope_wins_over_legacy_is_dot_false():
    projection = _project(HealTemporalScope.PERIODIC)

    assert projection.direct_events == ()
    assert len(projection.periodic_seeds) == 1
    assert projection.periodic_seeds[0].time_seconds == 2.0
    assert projection.delayed_seeds == ()
    assert projection.unresolved == ()
