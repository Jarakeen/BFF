from dataclasses import dataclass
from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from models.build_model import PlayerBuild
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle
import ui.rotation_generate_dd_role_evidence_support as dd_support


@dataclass(frozen=True)
class _Context:
    target_resistance: float | None = None
    fight_duration: float = 0.0


@dataclass(frozen=True)
class _RuntimeResult:
    resolved: bool
    context: _Context | None
    unresolved: tuple[str, ...] = ()


class _StaticContextService:
    def __init__(self) -> None:
        self.result = SimpleNamespace(resolved=True, unresolved=())

    def resolve(self, build, **kwargs):
        del build, kwargs
        return self.result


class _Registry:
    def load(self):
        return ()


class _PlanProvider:
    def __init__(self, runtime_resolver) -> None:
        self.runtime_resolver = runtime_resolver

    def evaluate_plan(self, candidate):
        del candidate
        raise AssertionError("not needed for runtime-binding fixture")


class _RecordingSupport(dd_support.RotationGenerateDDRoleEvidenceSupport):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.providers = []

    def _build_plan_evidence_provider(self, **kwargs):
        provider = _PlanProvider(kwargs["runtime_build_context_resolver"])
        self.providers.append(provider)
        return provider


class _RuntimeBuildContextService:
    calls = []

    def __init__(self, *, static_context_service) -> None:
        self.static_context_service = static_context_service

    def resolve(
        self,
        build,
        *,
        runtime_combat_state_resolver,
        time_seconds,
        sequence=None,
    ):
        self.calls.append(
            (build, runtime_combat_state_resolver, time_seconds, sequence)
        )
        return _RuntimeResult(resolved=True, context=_Context())


def _bundle() -> RotationCanonicalEvidenceBundle:
    return RotationCanonicalEvidenceBundle(
        encounter_id="test",
        encounter_name="Test",
        content_type="trial",
        demands=(),
        options=(),
        requirements=(),
        passives=(),
        evaluator_resolver=None,
        scorecard_resolver=None,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.35,
        target_resistance=18200.0,
    )


def test_dd_role_evidence_binds_final_runtime_context_to_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        dd_support,
        "RotationPlanRuntimeBuildContextService",
        _RuntimeBuildContextService,
    )
    _RuntimeBuildContextService.calls.clear()
    static = _StaticContextService()
    support = _RecordingSupport(
        database_path="unused.db",
        static_context_service=static,  # type: ignore[arg-type]
        periodic_runtime_semantics_registry=_Registry(),  # type: ignore[arg-type]
    )
    build = PlayerBuild(Name="Parse Cat", BuildName="DD", Role="DD")

    role_evidence = support.compose(player_build=build, evidence_bundle=_bundle())
    assert len(support.providers) == 1
    assert support.providers[0].runtime_resolver is None

    runtime_combat_state_resolver = object()
    snapshot = SimpleNamespace(
        plan=SimpleNamespace(duration_seconds=37.0),
        runtime_combat_state_resolver=runtime_combat_state_resolver,
    )
    runtime_provider = role_evidence.plan_evidence_provider.for_stabilized_snapshot(
        snapshot
    )

    assert runtime_provider is support.providers[1]
    assert runtime_provider.runtime_resolver is not None
    resolved = runtime_provider.runtime_resolver(12.5, 3)

    assert resolved.resolved is True
    assert resolved.context is not None
    assert resolved.context.target_resistance == 18200.0
    assert resolved.context.fight_duration == 37.0
    assert _RuntimeBuildContextService.calls == [
        (build, runtime_combat_state_resolver, 12.5, 3)
    ]
