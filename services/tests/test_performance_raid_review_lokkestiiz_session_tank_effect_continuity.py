from types import SimpleNamespace

from minmax.runtime_effect_window import RuntimeEffectActiveWindow
from services.performance_raid_review_lokkestiiz_pull_service import LokkestiizPullRaidReviewEvidence
from services.performance_raid_review_lokkestiiz_session_service import (
    LokkestiizRaidReviewPullRequest,
    PerformanceRaidReviewLokkestiizSessionService,
)
from services.performance_raid_review_observation_service import RaidReviewSource
from services.performance_raid_review_tank_effect_continuity_service import (
    RaidReviewTankEffectContinuityObservation,
    RaidReviewTankEffectContinuityResult,
    RaidReviewTankEffectRequirement,
)


class _Client:
    def get_fight(self, report_code, fight_id):
        return {"name": "Lokkestiiz", "startTime": 0.0, "endTime": 100000.0}


class _PerformanceService:
    client = _Client()


class _EventProvider:
    def events_for_fight(self, **kwargs):
        return ({"timestamp": 1000.0, "type": "applydebuff", "abilityName": "Major Breach"},)


class _PullService:
    def build(self, **kwargs):
        return LokkestiizPullRaidReviewEvidence((), (), (), ())


class _DDContinuityService:
    def measure(self, **kwargs):
        return SimpleNamespace(observations=(), unresolved=("No DPS actors were supplied for ground-continuity analysis.",))


class _EffectWindowService:
    def __init__(self):
        self.calls = []

    def build(self, events, **kwargs):
        self.calls.append((tuple(events), kwargs))
        return SimpleNamespace(
            windows=(
                RuntimeEffectActiveWindow(
                    effect_name="Major Breach",
                    source="esologs:actor:5",
                    target="esologs:actor:99",
                    start_time_seconds=0.0,
                    end_time_seconds=90.0,
                ),
            ),
            unresolved=(),
        )


class _TankEffectContinuityService:
    def __init__(self):
        self.calls = []

    def measure(self, **kwargs):
        self.calls.append(kwargs)
        requirement = tuple(kwargs["requirements"])[0]
        actor = next(actor for actor in kwargs["actors"] if actor.role == "Tank")
        return RaidReviewTankEffectContinuityResult(
            observations=(
                RaidReviewTankEffectContinuityObservation(
                    report_code=kwargs["report_code"],
                    fight_id=kwargs["fight_id"],
                    actor_id=actor.actor_id,
                    actor_label=actor.actor_label,
                    member_key=actor.member_key,
                    requirement_semantic_key=requirement.semantic_key,
                    requirement_label=requirement.label,
                    eligible_seconds=100.0,
                    covered_seconds=90.0,
                    coverage_percent=90.0,
                    active_effect_names=("Major Breach",),
                ),
            ),
            unresolved=(),
        )


class _Coordinator:
    def __init__(self):
        self.calls = []

    def review(self, sources, **kwargs):
        self.calls.append((tuple(sources), kwargs))
        return SimpleNamespace(
            unresolved=(),
            report=SimpleNamespace(encounter_name="Lokkestiiz"),
            collection=SimpleNamespace(observations=()),
            priorities=(),
        )


def test_session_projects_shared_windows_once_and_passes_tank_continuity_to_coordinator() -> None:
    effect_windows = _EffectWindowService()
    tank_continuity = _TankEffectContinuityService()
    coordinator = _Coordinator()
    service = PerformanceRaidReviewLokkestiizSessionService(
        _PerformanceService(),
        event_provider=_EventProvider(),
        pull_service=_PullService(),
        coordinator_service=coordinator,
        effect_window_service=effect_windows,
        dd_ground_continuity_service=_DDContinuityService(),
        tank_effect_continuity_service=tank_continuity,
    )
    source = RaidReviewSource("A", 1, 5, "Main Tank", "Tank", member_key="main-tank")
    requirement = RaidReviewTankEffectRequirement(
        semantic_key="major_breach_assignment",
        label="Major Breach",
        effect_names=("Major Breach",),
        source_actor_id=5,
    )

    result = service.review(
        (LokkestiizRaidReviewPullRequest("A", 1, 99, (source,)),),
        tank_effect_requirements=(requirement,),
    )

    assert len(effect_windows.calls) == 1
    assert effect_windows.calls[0][1]["effect_names"] == ("Major Breach",)
    assert len(tank_continuity.calls) == 1
    assert result.tank_effect_continuity[0].coverage_percent == 90.0
    _sources, kwargs = coordinator.calls[0]
    assert kwargs["tank_effect_continuity_observations"] == result.tank_effect_continuity
