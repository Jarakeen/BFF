from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.restoration_events import ResourceRestorationEvent
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_heavy_sustain_projection_service import (
    RotationHeavySustainProjectionService,
)


def _heavy(time: float = 5.0, sequence: int = 0) -> RotationAction:
    return RotationAction(time, sequence, RotationActionKind.HEAVY_ATTACK)


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=tuple(actions),
    )


class _RestorationService:
    def __init__(self, projection) -> None:
        self.projection = projection
        self.calls = []

    def project(self, **kwargs):
        self.calls.append(kwargs)
        return self.projection


class _ReplayService:
    def __init__(self) -> None:
        self.calls = []

    def replay(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(final_projection="replayed-sustain")


def _projection(*, action=None, event=None, unresolved=(), violations=()):
    resolutions = ()
    if action is not None:
        resolutions = (
            SimpleNamespace(action=action, restoration_event=event),
        )
    return SimpleNamespace(
        unresolved=tuple(unresolved),
        resolutions=resolutions,
        weapon_projection=SimpleNamespace(
            violations=tuple(violations),
            is_legal=not violations and not unresolved,
        ),
        is_resolved=not violations and not unresolved,
    )


def test_resolved_heavy_replays_before_scorecard_consumption() -> None:
    action = _heavy()
    event = ResourceRestorationEvent(
        time_seconds=7.0,
        resource=ResourceType.MAGICKA,
        amount=2500.0,
        source="verified resto heavy",
    )
    restoration = _RestorationService(_projection(action=action, event=event))
    replay = _ReplayService()
    service = RotationHeavySustainProjectionService(
        restoration_service=restoration,
        replay_service=replay,
    )

    result = service.project(
        character_build=object(),
        sustain_build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        plan=_plan(action),
        resource=ResourceType.MAGICKA,
        initial_bar="front",
        completion_evidence=(),
    )

    assert result.is_resolved is True
    assert result.sustain_projection == "replayed-sustain"
    assert result.unresolved == ()
    assert len(replay.calls) == 1
    resolver = replay.calls[0]["restoration_resolver"]
    assert resolver(action) is event


def test_unresolved_heavy_evidence_prevents_false_replay() -> None:
    restoration = _RestorationService(
        _projection(unresolved=("scheduled heavy lacks full-charge evidence",))
    )
    replay = _ReplayService()
    service = RotationHeavySustainProjectionService(
        restoration_service=restoration,
        replay_service=replay,
    )

    result = service.project(
        character_build=object(),
        sustain_build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        plan=_plan(_heavy()),
        resource=ResourceType.MAGICKA,
        initial_bar="front",
        completion_evidence=(),
    )

    assert result.is_resolved is False
    assert result.replay is None
    assert result.unresolved == ("scheduled heavy lacks full-charge evidence",)
    assert replay.calls == []


def test_weapon_projection_violation_is_hard_unresolved_for_sustain() -> None:
    action = _heavy()
    violation = SimpleNamespace(action=action, reason="heavy claims back but front is active")
    restoration = _RestorationService(_projection(violations=(violation,)))
    replay = _ReplayService()
    service = RotationHeavySustainProjectionService(
        restoration_service=restoration,
        replay_service=replay,
    )

    result = service.project(
        character_build=object(),
        sustain_build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        plan=_plan(action),
        resource=ResourceType.MAGICKA,
        initial_bar="front",
        completion_evidence=(),
    )

    assert result.is_resolved is False
    assert result.replay is None
    assert "weapon projection violation" in result.unresolved[0]
    assert "front is active" in result.unresolved[0]


def test_heavy_restore_for_other_resource_is_resolved_but_ignored() -> None:
    action = _heavy()
    stamina_event = ResourceRestorationEvent(
        time_seconds=7.0,
        resource=ResourceType.STAMINA,
        amount=2500.0,
        source="verified bow heavy",
    )
    restoration = _RestorationService(_projection(action=action, event=stamina_event))
    replay = _ReplayService()
    service = RotationHeavySustainProjectionService(
        restoration_service=restoration,
        replay_service=replay,
    )

    result = service.project(
        character_build=object(),
        sustain_build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        plan=_plan(action),
        resource=ResourceType.MAGICKA,
        initial_bar="front",
        completion_evidence=(),
    )

    assert result.is_resolved is True
    resolver = replay.calls[0]["restoration_resolver"]
    assert resolver(action) is None


def test_no_heavies_still_produces_normal_replayed_sustain_projection() -> None:
    restoration = _RestorationService(_projection())
    replay = _ReplayService()
    service = RotationHeavySustainProjectionService(
        restoration_service=restoration,
        replay_service=replay,
    )

    result = service.project(
        character_build=object(),
        sustain_build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        plan=_plan(),
        resource=ResourceType.MAGICKA,
        initial_bar="front",
        completion_evidence=(),
    )

    assert result.is_resolved is True
    assert result.sustain_projection == "replayed-sustain"
    assert len(replay.calls) == 1
