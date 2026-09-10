from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from models.build_model import PlayerBuild
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingService,
)


class _FakeCoefficients:
    def __init__(self, resolutions):
        self.resolutions = resolutions

    def resolve_name(self, name):
        return self.resolutions[name]


class _FakeComponents:
    def __init__(self, by_rank, *, excluded=()):
        self.by_rank = by_rank
        self.excluded = set(excluded)

    def get_for_skill_rank(self, skill_rank_id):
        return self.by_rank.get(skill_rank_id, ())

    def is_intentionally_excluded_caster_healing_component(
        self,
        *,
        skill_rank_id,
        coefficient_number,
    ):
        return (int(skill_rank_id), int(coefficient_number)) in self.excluded


class _FakeTooltipService:
    def __init__(self, *, resolution, result, classifications, excluded=()):
        self.coefficients = _FakeCoefficients({"Heal": resolution})
        self.components = _FakeComponents(
            {10: tuple(classifications)},
            excluded=excluded,
        )
        self.result = result
        self.calls = []

    def evaluate_entity_id(self, *, build, context, entity_id):
        self.calls.append(
            {
                "build": build,
                "context": context,
                "entity_id": entity_id,
            }
        )
        return self.result


def _resolution(rank_id=10, unresolved=()):
    rank = None if rank_id is None else SimpleNamespace(
        skill_rank_id=rank_id,
        entity_id="heal_entity",
    )
    return SimpleNamespace(rank=rank, unresolved=tuple(unresolved))


def _trace(number, value):
    return SimpleNamespace(coefficient_number=number, final_value=value)


def _actual_trace(number, value):
    return SimpleNamespace(coefficient_number=number, output_value=value)


def _result(*components, actual=(), unresolved=(), skill=True):
    resolved_skill = (
        SimpleNamespace(skill_rank_id=10, entity_id="heal_entity", name="Heal")
        if skill
        else None
    )
    return SimpleNamespace(
        skill=resolved_skill,
        components=tuple(components),
        component_actual_effect_trace=tuple(actual),
        unresolved=tuple(unresolved),
    )


def _classification(
    *,
    number=1,
    kind=SkillEffectKind.HEAL,
    is_periodic=False,
):
    return SkillComponentClassification(
        skill_rank_id=10,
        coefficient_number=number,
        effect_kind=kind,
        is_dot=is_periodic,
        source="test",
        confidence=1.0,
    )


def _plan(*actions):
    return RotationPlan(
        character_name="Test Healer",
        build_name="Heal",
        duration_seconds=20.0,
        actions=tuple(actions),
    )


def _action(
    time_seconds=1.0,
    sequence=0,
    kind=RotationActionKind.SKILL,
    bar="front",
):
    return RotationAction(
        time_seconds=time_seconds,
        sequence=sequence,
        kind=kind,
        name="Heal",
        bar=bar,
    )


def _service(*, resolution=None, result=None, classifications=(), excluded=()):
    tooltip = _FakeTooltipService(
        resolution=resolution or _resolution(),
        result=result or _result(_trace(1, 1000.0)),
        classifications=classifications,
        excluded=excluded,
    )
    return RotationHealerActionHealingService(".", tooltip_service=tooltip)


def test_projects_verified_direct_heal_at_cast_time():
    projection = _service(
        classifications=(_classification(is_periodic=False),)
    ).project(
        plan=_plan(_action(time_seconds=4.5, sequence=2)),
        build=PlayerBuild(),
        context=object(),
    )

    assert projection.unresolved == ()
    assert projection.periodic_seeds == ()
    assert len(projection.direct_events) == 1
    event = projection.direct_events[0]
    assert event.time_seconds == 4.5
    assert event.sequence == 2
    assert event.source_name == "Heal"
    assert event.coefficient_number == 1
    assert event.modeled_heal == 1000.0


def test_preserves_periodic_heal_as_runtime_seed_instead_of_fake_tick():
    projection = _service(
        classifications=(_classification(is_periodic=True),)
    ).project(
        plan=_plan(_action(time_seconds=3.0)),
        build=PlayerBuild(),
        context=object(),
    )

    assert projection.unresolved == ()
    assert projection.direct_events == ()
    assert len(projection.periodic_seeds) == 1
    seed = projection.periodic_seeds[0]
    assert seed.time_seconds == 3.0
    assert seed.modeled_heal == 1000.0


def test_uses_component_actual_effect_value_when_available():
    projection = _service(
        result=_result(
            _trace(1, 1000.0),
            actual=(_actual_trace(1, 1250.0),),
        ),
        classifications=(_classification(is_periodic=False),),
    ).project(
        plan=_plan(_action()),
        build=PlayerBuild(),
        context=object(),
    )

    assert projection.direct_events[0].modeled_heal == 1250.0


def test_non_healing_component_does_not_become_healing_consequence():
    projection = _service(
        classifications=(
            _classification(kind=SkillEffectKind.DAMAGE, is_periodic=False),
        )
    ).project(
        plan=_plan(_action()),
        build=PlayerBuild(),
        context=object(),
    )

    assert projection.direct_events == ()
    assert projection.periodic_seeds == ()
    assert projection.unresolved == ()


def test_missing_component_classification_fails_closed():
    projection = _service(classifications=()).project(
        plan=_plan(_action()),
        build=PlayerBuild(),
        context=object(),
    )

    assert projection.direct_events == ()
    assert projection.unresolved == (
        "Heal coefficient 1 at 1s: canonical component classification unavailable",
    )


def test_reviewed_external_component_exclusion_does_not_become_false_unresolved():
    projection = _service(
        result=_result(_trace(1, 1000.0), _trace(2, 500.0)),
        classifications=(_classification(number=1, is_periodic=False),),
        excluded=((10, 2),),
    ).project(
        plan=_plan(_action()),
        build=PlayerBuild(),
        context=object(),
    )

    assert projection.unresolved == ()
    assert [event.coefficient_number for event in projection.direct_events] == [1]


def test_unknown_direct_vs_periodic_identity_fails_closed():
    classification = SkillComponentClassification(
        skill_rank_id=10,
        coefficient_number=1,
        effect_kind=SkillEffectKind.HEAL,
        is_dot=None,
        source="test",
        confidence=1.0,
    )
    projection = _service(classifications=(classification,)).project(
        plan=_plan(_action()),
        build=PlayerBuild(),
        context=object(),
    )

    assert projection.direct_events == ()
    assert projection.periodic_seeds == ()
    assert projection.unresolved == (
        "Heal coefficient 1 at 1s: direct-versus-periodic heal identity unavailable",
    )


def test_unresolved_skill_name_is_reported_without_heal_projection():
    projection = _service(
        resolution=_resolution(rank_id=None, unresolved=("ambiguous heal name",)),
        result=_result(),
        classifications=(),
    ).project(
        plan=_plan(_action()),
        build=PlayerBuild(),
        context=object(),
    )

    assert projection.direct_events == ()
    assert projection.periodic_seeds == ()
    assert projection.unresolved == ("Heal at 1s: ambiguous heal name",)


def test_mixed_direct_and_periodic_components_remain_separate():
    projection = _service(
        result=_result(_trace(1, 800.0), _trace(2, 300.0)),
        classifications=(
            _classification(number=1, is_periodic=False),
            _classification(number=2, is_periodic=True),
        ),
    ).project(
        plan=_plan(_action(time_seconds=6.0)),
        build=PlayerBuild(),
        context=object(),
    )

    assert projection.unresolved == ()
    assert [(e.coefficient_number, e.modeled_heal) for e in projection.direct_events] == [
        (1, 800.0)
    ]
    assert [(e.coefficient_number, e.modeled_heal) for e in projection.periodic_seeds] == [
        (2, 300.0)
    ]


def test_non_skill_actions_do_not_create_healing_consequences():
    projection = _service(
        classifications=(_classification(is_periodic=False),)
    ).project(
        plan=_plan(
            RotationAction(
                time_seconds=1.0,
                sequence=0,
                kind=RotationActionKind.LIGHT_ATTACK,
                bar="front",
            ),
            RotationAction(
                time_seconds=2.0,
                sequence=0,
                kind=RotationActionKind.WAIT,
            ),
        ),
        build=PlayerBuild(),
        context=object(),
    )

    assert projection.direct_events == ()
    assert projection.periodic_seeds == ()
    assert projection.unresolved == ()


def test_explicit_bar_contexts_follow_each_scheduled_action_bar():
    service = _service(classifications=(_classification(is_periodic=False),))
    default_context = object()
    front_context = object()
    back_context = object()

    projection = service.project(
        plan=_plan(
            _action(time_seconds=1.0, sequence=0, bar="front"),
            _action(time_seconds=2.0, sequence=1, bar="back"),
        ),
        build=PlayerBuild(),
        context=default_context,
        contexts_by_bar={"front": front_context, "back": back_context},
    )

    assert projection.unresolved == ()
    assert [call["context"] for call in service.tooltip_service.calls] == [
        front_context,
        back_context,
    ]


def test_missing_explicit_bar_context_fails_closed_instead_of_using_default():
    service = _service(classifications=(_classification(is_periodic=False),))
    default_context = object()
    front_context = object()

    projection = service.project(
        plan=_plan(_action(time_seconds=2.0, bar="back")),
        build=PlayerBuild(),
        context=default_context,
        contexts_by_bar={"front": front_context},
    )

    assert projection.direct_events == ()
    assert projection.unresolved == (
        "Heal at 2s: static build context unavailable for back bar",
    )
    assert service.tooltip_service.calls == []
