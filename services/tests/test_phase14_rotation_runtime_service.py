from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from services.phase14_rotation_runtime_service import Phase14RotationRuntimeService
from ui.rotation_generation_support import RotationGenerationResult, RotationGenerationRequest


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=(),
    )


class _Generation:
    def __init__(self):
        self.calls = []
        self.recovery_stabilization = SimpleNamespace(stabilize=self._stabilize)

    def generate_with_evidence(self, *, build, request):
        self.calls.append(request)
        return RotationGenerationResult(
            plan=_plan(),
            duration_evidence=SimpleNamespace(rows=(), unresolved=()),
        )

    def _stabilize(self, **kwargs):
        plan = kwargs["generate"](None)
        return SimpleNamespace(
            plan=plan,
            replay=SimpleNamespace(final_projection="recovery-projection"),
            iterations=(),
            converged=True,
            termination_reason="stable_fixed_point",
        )


class _StaticResolution:
    contexts = (object(),)
    progression = SimpleNamespace(character_id="character-1")

    def maximum_amount_for(self, bar, resource):
        return 32000 if resource is ResourceType.MAGICKA else 18000

    def context_for(self, bar):
        return object()

    def maximum_events_for(self, plan, resource, *, initial_bar):
        return ()

    def displayed_recovery_resolver_for(self, plan, resource, *, initial_bar):
        return lambda _time: 1000


class _Static:
    progression_adapter = object()

    def resolve(self, build):
        return _StaticResolution()


class _Adapter:
    def adapt(self, build, *, character_id=None):
        return SimpleNamespace(build=object(), unresolved=())


class _Heavy:
    @staticmethod
    def completion_evidence_from_verified_reservations(plan):
        return ()

    @staticmethod
    def restoration_resolver_for_plan(**kwargs):
        return lambda _action: None


def _service(generation):
    return Phase14RotationRuntimeService(
        generation=generation,
        static_context=_Static(),
        heavy_sustain=_Heavy(),
        character_adapter=_Adapter(),
    )


def _build():
    return SimpleNamespace(
        FrontBarSkills=["Skill", "", "", "", "", ""],
        BackBarSkills=["", "", "", "", "", ""],
    )


def test_avoid_unless_mandatory_stays_on_baseline_generation() -> None:
    generation = _Generation()
    result = _service(generation).generate(
        build=_build(),
        request=RotationGenerationRequest(),
        heavy_behavior="Avoid unless mandatory",
        reserve_fraction=0.10,
    )

    assert len(generation.calls) == 1
    assert result.recovery_projection is None
    assert result.resource is ResourceType.MAGICKA


def test_use_when_needed_routes_through_recovery_heavy_stabilization() -> None:
    generation = _Generation()
    result = _service(generation).generate(
        build=_build(),
        request=RotationGenerationRequest(),
        heavy_behavior="Use when needed",
        reserve_fraction=0.20,
    )

    assert len(generation.calls) == 1
    assert result.recovery_projection == "recovery-projection"
    assert result.resource is ResourceType.MAGICKA
