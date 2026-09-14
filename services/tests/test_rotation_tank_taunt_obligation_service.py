from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_utility_effect import (
    SkillComponentUtilityEffect,
    SkillComponentUtilityEffectType,
)
from services.rotation_tank_taunt_obligation_service import (
    RotationTankTauntApplicationRequirement,
    RotationTankTauntObligationService,
)


class _CoefficientRepository:
    def __init__(self, *, rank=None, unresolved=()):
        self.rank = rank
        self.unresolved = tuple(unresolved)

    def resolve_name(self, name):
        return SimpleNamespace(rank=self.rank, unresolved=self.unresolved)


class _UtilityRepository:
    def __init__(self, effects_by_number):
        self.effects_by_number = dict(effects_by_number)
        self.calls = []

    def resolve(self, skill_rank_id, coefficient_number):
        self.calls.append((skill_rank_id, coefficient_number))
        return tuple(self.effects_by_number.get(coefficient_number, ()))


def _rank(*numbers):
    return SimpleNamespace(
        skill_rank_id=42,
        coefficients=tuple(
            SimpleNamespace(coefficient_number=number) for number in numbers
        ),
    )


def _taunt(number=2):
    return SkillComponentUtilityEffect(
        skill_rank_id=42,
        coefficient_number=number,
        effect_type=SkillComponentUtilityEffectType.TAUNT,
        evidence="Taunts the enemy",
    )


def _non_taunt(number=1):
    return SkillComponentUtilityEffect(
        skill_rank_id=42,
        coefficient_number=number,
        effect_type=SkillComponentUtilityEffectType.STUN,
        evidence="Stuns the enemy",
    )


def _service(*, rank=None, effects=None, unresolved=()):
    return RotationTankTauntObligationService(
        ".",
        coefficient_repository=_CoefficientRepository(
            rank=rank,
            unresolved=unresolved,
        ),
        utility_repository=_UtilityRepository(effects or {}),
    )


def _plan(*actions):
    return RotationPlan(
        character_name="Tank",
        build_name="Main Tank",
        duration_seconds=60.0,
        actions=tuple(actions),
    )


def _cast(time_seconds, *, name="Pierce Armor", bar="front", sequence=0):
    return RotationAction(
        time_seconds=time_seconds,
        sequence=sequence,
        kind=RotationActionKind.SKILL,
        name=name,
        bar=bar,
    )


def _requirement(**overrides):
    values = dict(
        requirement_id="boss-taunt",
        source_skill_name="Pierce Armor",
        window_start_seconds=10.0,
        window_end_seconds=20.0,
        minimum_applications=1,
        provenance=("reviewed encounter responsibility",),
    )
    values.update(overrides)
    return RotationTankTauntApplicationRequirement(**values)


def test_source_backed_taunt_cast_inside_window_satisfies_application_requirement():
    service = _service(
        rank=_rank(1, 2),
        effects={1: (_non_taunt(1),), 2: (_taunt(2),)},
    )

    result = service.assess(
        plan=_plan(_cast(9.0), _cast(12.0), _cast(21.0)),
        requirement=_requirement(),
    )

    assert result.resolved is True
    assert result.satisfied is True
    assert result.taunt_component_numbers == (2,)
    assert [item.time_seconds for item in result.applications] == [12.0]
    assert result.evidence == ("Pierce Armor coefficient 2: Taunts the enemy",)
    assert result.unresolved == ()


def test_minimum_application_count_is_explicit_policy_not_inferred_uptime():
    service = _service(rank=_rank(2), effects={2: (_taunt(2),)})

    result = service.assess(
        plan=_plan(_cast(11.0), _cast(18.0)),
        requirement=_requirement(minimum_applications=3),
    )

    assert result.resolved is True
    assert result.satisfied is False
    assert len(result.applications) == 2
    assert result.unresolved == ()


def test_bar_specific_taunt_requirement_counts_only_exact_bar_casts():
    service = _service(rank=_rank(2), effects={2: (_taunt(2),)})

    result = service.assess(
        plan=_plan(
            _cast(12.0, bar="back"),
            _cast(14.0, bar="front"),
        ),
        requirement=_requirement(bar="front"),
    )

    assert result.satisfied is True
    assert [(item.time_seconds, item.bar) for item in result.applications] == [
        (14.0, "front")
    ]


def test_same_named_cast_outside_explicit_window_does_not_satisfy_requirement():
    service = _service(rank=_rank(2), effects={2: (_taunt(2),)})

    result = service.assess(
        plan=_plan(_cast(9.999), _cast(20.001)),
        requirement=_requirement(),
    )

    assert result.resolved is True
    assert result.satisfied is False
    assert result.applications == ()


def test_exact_window_boundaries_are_inclusive():
    service = _service(rank=_rank(2), effects={2: (_taunt(2),)})

    result = service.assess(
        plan=_plan(_cast(10.0), _cast(20.0)),
        requirement=_requirement(minimum_applications=2),
    )

    assert result.satisfied is True
    assert [item.time_seconds for item in result.applications] == [10.0, 20.0]


def test_requested_source_skill_without_canonical_taunt_semantics_fails_closed():
    service = _service(rank=_rank(1), effects={1: (_non_taunt(1),)})

    result = service.assess(
        plan=_plan(_cast(12.0)),
        requirement=_requirement(),
    )

    assert result.resolved is False
    assert result.satisfied is False
    assert result.applications == ()
    assert result.unresolved == (
        "boss-taunt: Pierce Armor has no source-backed canonical taunt utility component",
    )


def test_unresolved_skill_identity_fails_closed_without_inspecting_schedule():
    service = _service(
        rank=None,
        unresolved=("Ambiguous skill name",),
    )

    result = service.assess(
        plan=_plan(_cast(12.0)),
        requirement=_requirement(),
    )

    assert result.resolved is False
    assert result.satisfied is False
    assert result.unresolved == ("boss-taunt: Ambiguous skill name",)


def test_other_actions_and_other_skill_names_do_not_count_as_taunt_applications():
    service = _service(rank=_rank(2), effects={2: (_taunt(2),)})

    result = service.assess(
        plan=_plan(
            RotationAction(
                time_seconds=12.0,
                sequence=0,
                kind=RotationActionKind.LIGHT_ATTACK,
                bar="front",
            ),
            _cast(13.0, name="Heroic Slash"),
        ),
        requirement=_requirement(),
    )

    assert result.resolved is True
    assert result.satisfied is False
    assert result.applications == ()
