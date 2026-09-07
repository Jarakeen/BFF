from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationAction, RotationActionKind
import tools.audit_phase13_saved_build_recovery_heavy_rotation as audit_module
from tools.audit_phase13_saved_build_recovery_heavy_rotation import (
    build_verified_heavy_restore_resolver,
)


def _heavy(*, time_seconds: float = 2.0, bar: str = "front") -> RotationAction:
    return RotationAction(
        time_seconds=time_seconds,
        sequence=0,
        kind=RotationActionKind.HEAVY_ATTACK,
        name="Heavy Attack",
        bar=bar,
    )


def test_audit_restore_resolver_places_restore_at_heavy_completion() -> None:
    resolver = build_verified_heavy_restore_resolver(
        amount=4200,
        channel_seconds=1.8,
        bar="front",
    )

    event = resolver(_heavy(time_seconds=2.0, bar="front"))

    assert event is not None
    assert event.time_seconds == pytest.approx(3.8)
    assert event.resource is ResourceType.MAGICKA
    assert event.amount == 4200
    assert "caller-supplied" in event.source.casefold()


def test_audit_restore_resolver_ignores_heavies_on_other_bar() -> None:
    resolver = build_verified_heavy_restore_resolver(
        amount=4200,
        channel_seconds=1.8,
        bar="front",
    )

    assert resolver(_heavy(bar="back")) is None


def test_audit_restore_resolver_ignores_non_heavy_actions() -> None:
    resolver = build_verified_heavy_restore_resolver(
        amount=4200,
        channel_seconds=1.8,
    )
    action = RotationAction(
        time_seconds=2.0,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name="Combat Prayer",
        bar="front",
    )

    assert resolver(action) is None


def test_audit_restore_resolver_rejects_invalid_evidence() -> None:
    with pytest.raises(ValueError, match="restore amount"):
        build_verified_heavy_restore_resolver(amount=0, channel_seconds=1.8)

    with pytest.raises(ValueError, match="channel"):
        build_verified_heavy_restore_resolver(amount=4200, channel_seconds=0)

    with pytest.raises(ValueError, match="restore bar"):
        build_verified_heavy_restore_resolver(
            amount=4200,
            channel_seconds=1.8,
            bar="middle",
        )


def test_audit_derives_maximum_magicka_from_phase4_full_pool_baseline(monkeypatch) -> None:
    generated_plan = SimpleNamespace(name="baseline plan")
    generation_calls = []
    sustain_calls = []

    class GenerationStub:
        def generate(self, *, build, request):
            generation_calls.append((build, request))
            return generated_plan

    class SustainStub:
        def __init__(self, *, database_path):
            self.database_path = database_path

        def evaluate(self, *, build, plan, resource):
            sustain_calls.append((build, plan, resource, self.database_path))
            timeline = SimpleNamespace(starting_amount=31109)
            return SimpleNamespace(run=SimpleNamespace(timeline=timeline))

    monkeypatch.setattr(audit_module, "RotationGenerationSupport", GenerationStub)
    monkeypatch.setattr(audit_module, "RotationSustainService", SustainStub)
    build = SimpleNamespace(Name="Magrat", BuildName="DF Healer")

    maximum = audit_module._baseline_maximum_magicka(
        build=build,
        duration_seconds=60.0,
        database_path=audit_module.DEFAULT_DATABASE,
    )

    assert maximum == 31109
    assert len(generation_calls) == 1
    assert generation_calls[0][0] is build
    assert generation_calls[0][1].duration_seconds == 60.0
    assert sustain_calls == [
        (build, generated_plan, ResourceType.MAGICKA, audit_module.DEFAULT_DATABASE)
    ]
