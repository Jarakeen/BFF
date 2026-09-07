from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from minmax.restoration_events import ResourceRestorationEvent
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from ui.rotation_generation_support import (
    RotationGenerationRequest,
    RotationGenerationResult,
    RotationGenerationSupport,
)


def _build() -> PlayerBuild:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")
    build.FrontBarSkills = ["Combat Prayer", "", "", "", "", ""]
    return build


def _restore(heavy):
    return ResourceRestorationEvent(
        time_seconds=float(heavy.time_seconds) + 1.8,
        resource=ResourceType.MAGICKA,
        amount=4000,
        source="verified test heavy restore",
    )


def test_stabilized_generation_requires_explicit_recovery_evidence() -> None:
    support = RotationGenerationSupport()
    base = RotationGenerationRequest(stabilize_recovery_heavies=True)

    with pytest.raises(ValueError, match="recovery_maximum_amount"):
        support.generate_with_evidence(build=_build(), request=base)

    with pytest.raises(ValueError, match="recovery_trigger_fraction"):
        support.generate_with_evidence(
            build=_build(),
            request=RotationGenerationRequest(
                stabilize_recovery_heavies=True,
                recovery_maximum_amount=30000,
            ),
        )

    with pytest.raises(ValueError, match="recovery_restoration_resolver"):
        support.generate_with_evidence(
            build=_build(),
            request=RotationGenerationRequest(
                stabilize_recovery_heavies=True,
                recovery_maximum_amount=30000,
                recovery_trigger_fraction=0.35,
            ),
        )


def test_stabilized_generation_feeds_replayed_pressure_back_through_one_pass_generation() -> None:
    generation_pressure = []
    evidence = SimpleNamespace(summary="final duration evidence")

    def replayed_pressure(context):
        return None

    class StabilizationStub:
        def __init__(self):
            self.calls = []

        def stabilize(self, **kwargs):
            self.calls.append(kwargs)
            first = kwargs["generate"](None)
            second = kwargs["generate"](replayed_pressure)
            return SimpleNamespace(
                plan=second,
                replay=SimpleNamespace(),
                iterations=(SimpleNamespace(plan=first), SimpleNamespace(plan=second)),
                converged=True,
            )

    stabilizer = StabilizationStub()

    class Support(RotationGenerationSupport):
        def _generate_once(self, *, build, request):
            generation_pressure.append(request.recovery_pressure_resolver)
            has_pressure = request.recovery_pressure_resolver is not None
            plan = RotationPlan(
                character_name="Magrat",
                build_name="DF Healer",
                duration_seconds=20.0,
                actions=(
                    RotationAction(
                        time_seconds=2.0,
                        sequence=0,
                        kind=RotationActionKind.HEAVY_ATTACK,
                        name="Heavy Attack" if not has_pressure else "Stabilized Heavy Attack",
                        bar="front",
                    ),
                ),
            )
            return RotationGenerationResult(plan=plan, duration_evidence=evidence)

    support = Support(recovery_stabilization=stabilizer)
    result = support.generate_with_evidence(
        build=_build(),
        request=RotationGenerationRequest(
            stabilize_recovery_heavies=True,
            recovery_stabilization_resource=ResourceType.MAGICKA,
            recovery_maximum_amount=30000,
            recovery_trigger_fraction=0.35,
            recovery_restoration_resolver=_restore,
            recovery_stabilization_max_iterations=4,
        ),
    )

    assert generation_pressure == [None, replayed_pressure]
    assert result.plan.actions[0].name == "Stabilized Heavy Attack"
    assert result.duration_evidence is evidence
    assert result.recovery_stabilization.converged is True
    assert len(stabilizer.calls) == 1
    call = stabilizer.calls[0]
    assert call["resource"] is ResourceType.MAGICKA
    assert call["maximum_amount"] == 30000
    assert call["trigger_fraction"] == 0.35
    assert call["restoration_resolver"] is _restore
    assert call["max_iterations"] == 4


def test_default_generation_result_has_no_recovery_stabilization_metadata() -> None:
    result = RotationGenerationSupport().generate_with_evidence(
        build=_build(),
        request=RotationGenerationRequest(duration_seconds=3.0),
    )

    assert result.recovery_stabilization is None
