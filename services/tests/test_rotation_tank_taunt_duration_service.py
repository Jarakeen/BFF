from types import SimpleNamespace

from engine.config import DEFAULT_DATABASE
from minmax.skill_component_utility_effect import (
    SkillComponentUtilityEffect,
    SkillComponentUtilityEffectType,
)
from services.rotation_tank_taunt_duration_service import (
    RotationTankTauntDurationService,
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

    def resolve(self, skill_rank_id, coefficient_number):
        return tuple(self.effects_by_number.get(coefficient_number, ()))


def _rank(*numbers):
    return SimpleNamespace(
        name="Pierce Armor",
        skill_rank_id=42,
        ability_id=84,
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


def _stun(number=1):
    return SkillComponentUtilityEffect(
        skill_rank_id=42,
        coefficient_number=number,
        effect_type=SkillComponentUtilityEffectType.STUN,
        evidence="Stuns the enemy",
    )


def _duration_resolution(*durations):
    return SimpleNamespace(
        evidence=tuple(
            SimpleNamespace(
                duration_seconds=value,
                effect_name=f"effect_{index}",
                source="canonical test evidence",
            )
            for index, value in enumerate(durations, start=1)
        ),
        unresolved=(),
    )


def _service(*, effects, durations=(), rank=None, unresolved=()):
    resolved_rank = _rank(1, 2) if rank is None else rank
    return RotationTankTauntDurationService(
        "unused.db",
        coefficient_repository=_CoefficientRepository(
            rank=resolved_rank,
            unresolved=unresolved,
        ),
        utility_repository=_UtilityRepository(effects),
        duration_resolver=lambda _name: _duration_resolution(*durations),
    )


def test_unique_positive_canonical_duration_resolves_for_source_backed_taunt() -> None:
    result = _service(
        effects={1: (_stun(1),), 2: (_taunt(2),)},
        durations=(15.0, 15.0),
    ).resolve("Pierce Armor")

    assert result.resolved is True
    assert result.duration_seconds == 15.0
    assert result.taunt_component_numbers == (2,)
    assert result.unresolved == ()
    assert any("duration 15s" in item for item in result.evidence)


def test_multiple_distinct_canonical_durations_fail_closed() -> None:
    result = _service(
        effects={2: (_taunt(2),)},
        durations=(10.0, 15.0),
    ).resolve("Pierce Armor")

    assert result.resolved is False
    assert result.duration_seconds is None
    assert result.unresolved == (
        "Pierce Armor: multiple canonical durations require taunt-component temporal binding (10s, 15s)",
    )


def test_non_taunt_source_cannot_borrow_duration_as_taunt_duration() -> None:
    result = _service(
        effects={1: (_stun(1),)},
        durations=(15.0,),
        rank=_rank(1),
    ).resolve("Pierce Armor")

    assert result.resolved is False
    assert result.duration_seconds is None
    assert result.unresolved == (
        "Pierce Armor has no source-backed canonical taunt utility component",
    )


def test_missing_positive_duration_stays_unresolved() -> None:
    service = RotationTankTauntDurationService(
        "unused.db",
        coefficient_repository=_CoefficientRepository(rank=_rank(2)),
        utility_repository=_UtilityRepository({2: (_taunt(2),)}),
        duration_resolver=lambda _name: SimpleNamespace(
            evidence=(),
            unresolved=("no positive canonical duration evidence found for Pierce Armor",),
        ),
    )

    result = service.resolve("Pierce Armor")

    assert result.resolved is False
    assert result.duration_seconds is None
    assert result.unresolved == (
        "no positive canonical duration evidence found for Pierce Armor",
    )


def test_real_database_pierce_armor_resolves_one_canonical_taunt_duration() -> None:
    assert DEFAULT_DATABASE.is_file(), f"canonical ESO database is missing: {DEFAULT_DATABASE}"

    result = RotationTankTauntDurationService(DEFAULT_DATABASE).resolve("Pierce Armor")

    assert result.resolved is True, result.unresolved
    assert result.duration_seconds == 15.0
    assert result.taunt_component_numbers
    assert any("duration 15s" in item for item in result.evidence)


def test_taunt_duration_resolution_does_not_create_refresh_policy() -> None:
    result = _service(
        effects={2: (_taunt(2),)},
        durations=(15.0,),
    ).resolve("Pierce Armor")

    assert result.duration_seconds == 15.0
    assert not hasattr(result, "refresh_seconds")
    assert not hasattr(result, "recast_interval_seconds")
    assert not hasattr(result, "maintenance_window")
