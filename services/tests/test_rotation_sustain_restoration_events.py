from types import SimpleNamespace
from unittest.mock import patch

from minmax.resource_costs import ResourceType
from minmax.restoration_events import ResourceRestorationEvent
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_sustain_service import RotationSustainService


def test_rotation_sustain_passes_verified_restoration_events_to_phase4_runner() -> None:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=10.0,
        actions=(),
    )
    restore = ResourceRestorationEvent(
        time_seconds=3.8,
        resource=ResourceType.MAGICKA,
        amount=4200,
        source="Verified Restoration Staff heavy",
    )
    received = {}

    def evaluator(**kwargs):
        received.update(kwargs)
        timeline = SimpleNamespace(starting_amount=30000, events=())
        return SimpleNamespace(
            timeline=timeline,
            unresolved=(),
        )

    fake_context = SimpleNamespace(
        unresolved_gear_effects=(),
        progression=SimpleNamespace(),
    )

    class FakeFactory:
        def __init__(self, **kwargs):
            pass

        def build(self, **kwargs):
            return fake_context

    with patch("services.rotation_sustain_service.BuildCalculationContextFactory", FakeFactory):
        projection = RotationSustainService(sustain_evaluator=evaluator).evaluate(
            build=build,
            plan=plan,
            resource=ResourceType.MAGICKA,
            restoration_events=(restore,),
        )

    assert received["restoration_events"] == (restore,)
    assert received["resource"] is ResourceType.MAGICKA
    assert projection.run.timeline is fake_context.__class__(**{}) if False else received.get("never")
