from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from minmax.ultimate_resource_timeline import UltimateGenerationEvent
from services.extreme_saved_rotation_resource_record_service import (
    ExtremeSavedRotationResourceRecordService,
)


class _Catalog:
    def load(self):
        return {
            "builds": [
                {
                    "build_id": "magrat-df",
                    "name": "DF Healer",
                    "payload": {
                        "Name": "Magrat",
                        "Gamertag": "Jarakeen",
                        "BuildName": "DF Healer",
                    },
                }
            ]
        }


class _Artifacts:
    def __init__(self, plan):
        self.plan = plan

    def get_rotation_plan(self, build_id):
        assert build_id == "magrat-df"
        return self.plan


class _SustainService:
    def __init__(self):
        self.calls = []

    def evaluate(self, *, build, plan, resource, restoration_events=()):
        self.calls.append((resource, tuple(restoration_events)))
        if resource is ResourceType.MAGICKA:
            sustain = SimpleNamespace(
                starting_amount=100,
                ending_amount=80,
                minimum_amount=40,
                sustains=True,
                first_failure=None,
            )
            events = (object(), object())
        else:
            # Better raw net value, but no actual Stamina spending in the plan.
            # It must not beat the genuinely exercised Magicka branch.
            sustain = SimpleNamespace(
                starting_amount=100,
                ending_amount=100,
                minimum_amount=100,
                sustains=True,
                first_failure=None,
            )
            events = ()
        run = SimpleNamespace(
            sustain=sustain,
            action_cost_events=events,
        )
        return SimpleNamespace(run=run, unresolved=())


class _PotionRuntimeService:
    def __init__(self, events=()):
        self.events = tuple(events)
        self.calls = []

    def resolve_restoration_events(self, build, *, plan):
        self.calls.append((build, plan))
        return SimpleNamespace(events=self.events, unresolved=())


class _CombatUltimateSource:
    def events_from_plan(self, *, plan, assume_scheduled_attacks_damage):
        assert assume_scheduled_attacks_damage is True
        return (
            UltimateGenerationEvent(time_seconds=1.0, amount=3.0, source="base combat Ultimate generation"),
            UltimateGenerationEvent(time_seconds=2.0, amount=3.0, source="base combat Ultimate generation"),
        )


def _build():
    return SimpleNamespace(Name="Magrat", Gamertag="Jarakeen", BuildName="DF Healer")


def _plan():
    return SimpleNamespace(duration_seconds=20.0, unresolved=())


def _service(plan=None, *, potion_runtime_service=None, sustain_service=None):
    return ExtremeSavedRotationResourceRecordService(
        "unused/eso.db",
        artifact_service=_Artifacts(_plan() if plan is None else plan),
        catalog_service=_Catalog(),
        sustain_service=sustain_service or _SustainService(),
        potion_runtime_service=potion_runtime_service or _PotionRuntimeService(),
        combat_ultimate_source=_CombatUltimateSource(),
    )


def test_resource_sustain_excludes_unused_primary_resource_branch() -> None:
    result = _service().resource_sustain(_build())

    assert result.resource is ResourceType.MAGICKA
    assert result.record is not None
    assert result.action_cost_event_count == 2
    assert result.record.net_resource == -20
    assert result.record.net_resource_per_second == pytest.approx(-1.0)
    assert "Unused primary-resource branches" in result.evidence[-1]
    assert any("Global Extreme sustain search" in item for item in result.unresolved)


def test_ultimate_generation_reuses_constructive_combat_trigger_source() -> None:
    result = _service().ultimate_generation(_build())

    assert result.record is not None
    assert result.record.total_generated == pytest.approx(6.0)
    assert result.record.generated_per_second == pytest.approx(0.3)
    assert result.record.event_count == 2
    assert any("successful damaging triggers" in item for item in result.evidence)
    assert any("Heroism" in item for item in result.unresolved)


def test_missing_saved_rotation_fails_closed_for_both_records() -> None:
    service = _service(plan=False)
    service.artifact_service = _Artifacts(None)

    sustain = service.resource_sustain(_build())
    ultimate = service.ultimate_generation(_build())

    assert sustain.record is None
    assert sustain.resource is None
    assert "no saved canonical RotationPlan" in sustain.unresolved[0]
    assert ultimate.record is None
    assert "no saved canonical RotationPlan" in ultimate.unresolved[0]


def test_resource_sustain_includes_scheduled_potion_restoration_evidence() -> None:
    potion_event = object()
    potion_runtime = _PotionRuntimeService((potion_event,))
    sustain = _SustainService()
    service = _service(potion_runtime_service=potion_runtime, sustain_service=sustain)
    build = _build()

    result = service.resource_sustain(build)

    assert sustain.calls == [
        (ResourceType.MAGICKA, (potion_event,)),
        (ResourceType.STAMINA, (potion_event,)),
    ]
    assert potion_runtime.calls == [(build, service.artifact_service.plan)]
    assert any("1 scheduled potion restoration events" in item for item in result.evidence)
