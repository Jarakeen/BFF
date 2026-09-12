from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from services.rotation_dd_action_damage_event_service import (
    RotationDDActionDamageEventService,
)


class _FakeCoefficients:
    def __init__(self, resolutions):
        self.resolutions = resolutions

    def resolve_name(self, name):
        return self.resolutions[name]


class _FakeComponents:
    def __init__(self, by_rank):
        self.by_rank = by_rank

    def get_for_skill_rank(self, skill_rank_id):
        return self.by_rank.get(skill_rank_id, ())


class _FakeCalculator:
    def __init__(self, results):
        self.results = results

    def evaluate_name(self, name, context):
        return self.results[name]


def _resolution(rank_id=10, unresolved=()):
    rank = None if rank_id is None else SimpleNamespace(skill_rank_id=rank_id)
    return SimpleNamespace(rank=rank, unresolved=tuple(unresolved))


def _result(*components, unresolved=()):
    return SimpleNamespace(components=tuple(components), unresolved=tuple(unresolved))


def _trace(number, value):
    return SimpleNamespace(coefficient_number=number, final_value=value)


def _plan(*actions):
    return RotationPlan(
        character_name="Test DD",
        build_name="Parse",
        duration_seconds=20.0,
        actions=tuple(actions),
    )


def _action(time_seconds=1.0, sequence=0, kind=RotationActionKind.SKILL, name="Hit"):
    return RotationAction(
        time_seconds=time_seconds,
        sequence=sequence,
        kind=kind,
        name=name,
        bar="front" if kind is not RotationActionKind.BAR_SWAP else "back",
    )


def _classification(
    *,
    number=1,
    kind=SkillEffectKind.DAMAGE,
    damage_type="flame",
    is_dot=False,
    is_aoe=False,
    can_crit=True,
):
    return SkillComponentClassification(
        skill_rank_id=10,
        coefficient_number=number,
        effect_kind=kind,
        damage_type=damage_type,
        is_dot=is_dot,
        is_aoe=is_aoe,
        can_crit=can_crit,
        source="test",
        confidence=1.0,
    )


def _service(*, resolution=None, result=None, classifications=()):
    return RotationDDActionDamageEventService(
        ".",
        coefficient_repository=_FakeCoefficients(
            {"Hit": resolution or _resolution()}
        ),
        component_repository=_FakeComponents({10: tuple(classifications)}),
        calculator=_FakeCalculator(
            {"Hit": result or _result(_trace(1, 1234.5))}
        ),
    )


def test_projects_verified_direct_damage_component_at_cast_time():
    service = _service(classifications=(_classification(),))

    projection = service.project(plan=_plan(_action(time_seconds=4.5)), context=object())

    assert projection.unresolved == ()
    assert projection.dot_components == ()
    assert len(projection.events) == 1
    event = projection.events[0]
    assert event.time_seconds == 4.5
    assert event.source_name == "Hit"
    assert event.coefficient_number == 1
    assert event.event.base_value == 1234.5
    assert event.event.scaling_coefficient == 0.0
    assert event.event.damage_type == "flame"
    assert event.event.can_crit is True
    assert event.event.is_dot is False
    assert event.event.is_aoe is False


def test_preserves_verified_damage_identity_flags():
    service = _service(
        classifications=(
            _classification(damage_type="physical", is_aoe=True, can_crit=False),
        )
    )

    projection = service.project(plan=_plan(_action()), context=object())

    event = projection.events[0].event
    assert event.damage_type == "physical"
    assert event.is_aoe is True
    assert event.can_crit is False


def test_non_damage_component_is_not_projected_as_damage():
    service = _service(
        classifications=(
            _classification(kind=SkillEffectKind.HEAL, damage_type=None, is_dot=None, is_aoe=None, can_crit=None),
        )
    )

    projection = service.project(plan=_plan(_action()), context=object())

    assert projection.events == ()
    assert projection.dot_components == ()
    assert projection.unresolved == ()


def test_dot_component_is_preserved_as_runtime_seed():
    service = _service(classifications=(_classification(is_dot=True),))

    projection = service.project(plan=_plan(_action()), context=object())

    assert projection.events == ()
    assert projection.unresolved == ()
    assert len(projection.dot_components) == 1
    seed = projection.dot_components[0]
    assert seed.cast_time_seconds == 1.0
    assert seed.source_name == "Hit"
    assert seed.coefficient_number == 1
    assert seed.event.base_value == 1234.5
    assert seed.event.is_dot is True


def test_incomplete_damage_identity_fails_closed():
    service = _service(
        classifications=(
            _classification(can_crit=None),
        )
    )

    projection = service.project(plan=_plan(_action()), context=object())

    assert projection.events == ()
    assert projection.dot_components == ()
    assert projection.unresolved == (
        "Hit coefficient 1 at 1s: damage identity is incomplete",
    )


def test_missing_component_classification_fails_closed():
    service = _service(classifications=())

    projection = service.project(plan=_plan(_action()), context=object())

    assert projection.events == ()
    assert projection.unresolved == (
        "Hit coefficient 1 at 1s: canonical component classification unavailable",
    )


def test_unresolved_skill_name_is_reported_and_not_projected():
    service = _service(
        resolution=_resolution(rank_id=None, unresolved=("ambiguous skill name",)),
        result=_result(),
        classifications=(),
    )

    projection = service.project(plan=_plan(_action()), context=object())

    assert projection.events == ()
    assert projection.unresolved == ("Hit at 1s: ambiguous skill name",)


def test_weapon_attacks_fail_closed_until_canonical_damage_projection_exists():
    service = _service(classifications=(_classification(),))
    plan = _plan(
        RotationAction(
            time_seconds=1.0,
            sequence=0,
            kind=RotationActionKind.LIGHT_ATTACK,
            bar="front",
        ),
        RotationAction(
            time_seconds=2.0,
            sequence=0,
            kind=RotationActionKind.HEAVY_ATTACK,
            bar="front",
        ),
        RotationAction(
            time_seconds=3.0,
            sequence=0,
            kind=RotationActionKind.WAIT,
        ),
    )

    projection = service.project(plan=plan, context=object())

    assert projection.events == ()
    assert projection.dot_components == ()
    assert projection.unresolved == (
        "light attack at 1s: canonical weapon-attack damage projection unavailable",
        "heavy attack at 2s: canonical weapon-attack damage projection unavailable",
    )


def test_calculator_unresolved_is_preserved_alongside_resolved_direct_event():
    service = _service(
        result=_result(_trace(1, 1234.5), unresolved=("secondary coefficient unsupported",)),
        classifications=(_classification(),),
    )

    projection = service.project(plan=_plan(_action()), context=object())

    assert len(projection.events) == 1
    assert projection.unresolved == (
        "Hit at 1s: secondary coefficient unsupported",
    )
