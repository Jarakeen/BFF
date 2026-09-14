from __future__ import annotations

from types import SimpleNamespace

from engine.config import DEFAULT_DATABASE
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_taunt_maintenance_service import (
    RotationTankTauntMaintenanceRequirement,
    RotationTankTauntMaintenanceService,
)


class _DurationService:
    def __init__(self, duration=15.0, *, unresolved=()):
        self.duration = duration
        self.unresolved = tuple(unresolved)

    def resolve(self, source_name):
        if self.unresolved:
            return SimpleNamespace(
                resolved=False,
                duration_seconds=None,
                evidence=(),
                unresolved=self.unresolved,
            )
        return SimpleNamespace(
            resolved=True,
            duration_seconds=self.duration,
            evidence=(f"{source_name} taunt duration {self.duration:g}s",),
            unresolved=(),
        )


def _service(duration=15.0, *, unresolved=()):
    return RotationTankTauntMaintenanceService(
        "unused.db",
        duration_service=_DurationService(duration, unresolved=unresolved),
    )


def _cast(time_seconds, *, target="boss", bar="front", name="Pierce Armor", sequence=0):
    return RotationAction(
        time_seconds=time_seconds,
        sequence=sequence,
        kind=RotationActionKind.SKILL,
        name=name,
        bar=bar,
        target_key=target,
    )


def _plan(*actions, duration=60.0):
    return RotationPlan(
        character_name="Tank",
        build_name="Main Tank",
        duration_seconds=duration,
        actions=tuple(actions),
    )


def _requirement(**overrides):
    values = dict(
        requirement_id="boss_maintenance",
        source_skill_name="Pierce Armor",
        target_key="boss",
        active_start_seconds=0.0,
        active_end_seconds=30.0,
        bar="front",
        provenance=("reviewed tank responsibility",),
    )
    values.update(overrides)
    return RotationTankTauntMaintenanceRequirement(**values)


def _candidate(plan):
    return GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=plan,
        refresh_leads=(),
        action_claims=(),
    )


def test_exact_expiry_recast_keeps_target_continuously_taunted() -> None:
    result = _service().assess(
        plan=_plan(_cast(0.0), _cast(15.0)),
        requirement=_requirement(),
    )

    assert result.resolved is True
    assert result.satisfied is True
    assert result.duration_seconds == 15.0
    assert result.uncovered_windows == ()
    assert result.covered_seconds == 30.0


def test_small_gap_between_recasts_fails_continuous_maintenance() -> None:
    result = _service().assess(
        plan=_plan(_cast(0.0), _cast(15.2)),
        requirement=_requirement(),
    )

    assert result.resolved is True
    assert result.satisfied is False
    assert result.uncovered_windows == ((15.0, 15.2),)


def test_pre_window_cast_may_cover_start_of_reviewed_responsibility() -> None:
    requirement = _requirement(active_start_seconds=10.0, active_end_seconds=25.0)
    result = _service().assess(
        plan=_plan(_cast(5.0), _cast(20.0)),
        requirement=requirement,
    )

    assert result.satisfied is True
    assert result.uncovered_windows == ()


def test_wrong_target_does_not_maintain_requested_target() -> None:
    result = _service().assess(
        plan=_plan(_cast(0.0, target="add"), _cast(15.0, target="add")),
        requirement=_requirement(),
    )

    assert result.satisfied is False
    assert result.matching_casts == ()
    assert result.uncovered_windows == ((0.0, 30.0),)


def test_unbound_target_does_not_satisfy_target_specific_maintenance() -> None:
    unbound = RotationAction(
        time_seconds=0.0,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name="Pierce Armor",
        bar="front",
    )
    result = _service().assess(
        plan=_plan(unbound, _cast(15.0)),
        requirement=_requirement(),
    )

    assert result.satisfied is False
    assert result.uncovered_windows == ((0.0, 15.0),)


def test_bar_requirement_filters_matching_taunts() -> None:
    result = _service().assess(
        plan=_plan(_cast(0.0, bar="back"), _cast(15.0, bar="back")),
        requirement=_requirement(bar="front"),
    )

    assert result.satisfied is False
    assert result.matching_casts == ()


def test_unresolved_canonical_duration_fails_closed() -> None:
    result = _service(
        unresolved=("Pierce Armor: canonical taunt duration unresolved",)
    ).assess(
        plan=_plan(_cast(0.0), _cast(15.0)),
        requirement=_requirement(),
    )

    assert result.resolved is False
    assert result.satisfied is False
    assert result.duration_seconds is None
    assert result.unresolved == (
        "boss_maintenance: Pierce Armor: canonical taunt duration unresolved",
    )


def test_candidate_hard_obligation_reports_target_specific_gap() -> None:
    evidence = _service().evaluate_candidate(
        candidate=_candidate(_plan(_cast(0.0), _cast(16.0))),
        requirements=(_requirement(),),
    )

    assert evidence.satisfied is False
    assert evidence.reasons == (
        "boss_maintenance: target boss taunt maintenance has uncovered window(s) 15-16s",
    )


def test_candidate_hard_obligation_passes_for_continuous_coverage() -> None:
    evidence = _service().evaluate_candidate(
        candidate=_candidate(_plan(_cast(0.0), _cast(14.9), _cast(29.8))),
        requirements=(_requirement(active_end_seconds=40.0),),
    )

    assert evidence.satisfied is True
    assert evidence.reasons == (
        "boss_maintenance: target boss continuously taunted for 40s",
    )


def test_no_requirements_is_unresolved_not_automatic_pass() -> None:
    evidence = _service().evaluate_candidate(
        candidate=_candidate(_plan()),
        requirements=(),
    )

    assert evidence.satisfied is None
    assert "no explicit target-specific maintenance requirement" in evidence.reasons[0]


def test_duplicate_requirement_ids_fail_closed() -> None:
    requirement = _requirement()
    try:
        _service().evaluate_candidate(
            candidate=_candidate(_plan()),
            requirements=(requirement, requirement),
        )
    except ValueError as exc:
        assert "duplicate tank taunt maintenance requirement id" in str(exc)
    else:
        raise AssertionError("Expected duplicate maintenance requirement IDs to fail")


def test_real_database_pierce_armor_duration_drives_continuous_maintenance() -> None:
    assert DEFAULT_DATABASE.is_file(), f"canonical ESO database is missing: {DEFAULT_DATABASE}"

    result = RotationTankTauntMaintenanceService(DEFAULT_DATABASE).assess(
        plan=_plan(
            _cast(0.0, target="taleria"),
            _cast(15.0, target="taleria"),
        ),
        requirement=_requirement(
            target_key="taleria",
            active_start_seconds=0.0,
            active_end_seconds=30.0,
        ),
    )

    assert result.resolved is True, result.unresolved
    assert result.duration_seconds == 15.0
    assert result.satisfied is True
    assert result.uncovered_windows == ()
