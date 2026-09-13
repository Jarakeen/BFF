from services.rotation_candidate_target_health_aware_skill_damage_factory_service import (
    RotationCandidateTargetHealthAwareSkillDamageFactoryService,
)
from services.rotation_candidate_target_health_aware_skill_damage_service import (
    RotationCandidateTargetHealthAwareSkillDamageService,
)
from services.rotation_periodic_target_health_semantics_service import (
    PeriodicTargetHealthTimingPolicy,
    RotationPeriodicTargetHealthSemantics,
)


class _Base:
    pass


def _semantics():
    return (
        RotationPeriodicTargetHealthSemantics(
            skill_entity_id="Periodic Execute",
            coefficient_number=1,
            policy=PeriodicTargetHealthTimingPolicy.DYNAMIC_AT_TICK,
            source="reviewed test evidence",
        ),
    )


def _snapshot_resolver(time_seconds, sequence=None):
    del time_seconds, sequence
    return None


def test_factory_is_inert_without_reviewed_semantics() -> None:
    base = _Base()
    factory = RotationCandidateTargetHealthAwareSkillDamageFactoryService(
        semantics=(),
        snapshot_resolver=_snapshot_resolver,
        target_identity="boss",
    )

    assert factory.enabled is False
    assert factory.wrap(base) is base  # type: ignore[arg-type]


def test_factory_is_inert_without_runtime_snapshot_resolver() -> None:
    base = _Base()
    factory = RotationCandidateTargetHealthAwareSkillDamageFactoryService(
        semantics=_semantics(),
        snapshot_resolver=None,
        target_identity="boss",
    )

    assert factory.enabled is False
    assert factory.wrap(base) is base  # type: ignore[arg-type]


def test_factory_is_inert_without_target_identity() -> None:
    base = _Base()
    factory = RotationCandidateTargetHealthAwareSkillDamageFactoryService(
        semantics=_semantics(),
        snapshot_resolver=_snapshot_resolver,
        target_identity="",
    )

    assert factory.enabled is False
    assert factory.wrap(base) is base  # type: ignore[arg-type]


def test_factory_wraps_only_when_all_authoritative_inputs_exist() -> None:
    base = _Base()
    factory = RotationCandidateTargetHealthAwareSkillDamageFactoryService(
        semantics=_semantics(),
        snapshot_resolver=_snapshot_resolver,
        target_identity="boss",
    )

    wrapped = factory.wrap(base)  # type: ignore[arg-type]

    assert factory.enabled is True
    assert isinstance(wrapped, RotationCandidateTargetHealthAwareSkillDamageService)
    assert wrapped.base is base
    assert wrapped.periodic_target_health_bridge.base is base
    assert wrapped.periodic_target_health_bridge.snapshot_resolver is _snapshot_resolver
    assert wrapped.periodic_target_health_bridge.target_identity == "boss"
