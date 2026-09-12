from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from ui.rotation_generate_application_context_provider import (
    RotationGenerateApplicationContextProvider,
)


class _StaticContext:
    def __init__(self, *, resolved=True, unresolved=(), maximum=32123) -> None:
        self.resolved = resolved
        self.unresolved = tuple(unresolved)
        self.maximum = maximum
        self.progression = SimpleNamespace(character_id="magrat-id")

    def maximum_amount_for(self, bar, resource):
        assert bar == "front"
        assert resource is ResourceType.MAGICKA
        return self.maximum


class _StaticContextService:
    def __init__(self, result) -> None:
        self.result = result
        self.calls = []

    def resolve(self, build):
        self.calls.append(build)
        return self.result


class _PolicyProvider:
    def __init__(self, result) -> None:
        self.result = result
        self.calls = []

    def policies_for(self, encounter_id):
        self.calls.append(encounter_id)
        return self.result


class _Page:
    def __init__(self) -> None:
        self.build = SimpleNamespace(Role="Healer")
        self.encounter_id = "rockgrove_xalvakka"
        self.policy = {
            "resource": ResourceType.MAGICKA,
            "trigger_fraction": 0.35,
        }

    def _selected_build(self):
        return self.build

    def selected_encounter_id(self):
        return self.encounter_id

    def canonical_recovery_policy(self):
        return dict(self.policy)


def test_live_context_uses_exact_build_encounter_explicit_policy_and_static_maximum() -> None:
    static = _StaticContextService(_StaticContext())
    demand_policy = object()
    policies = _PolicyProvider((demand_policy,))
    composer = object()
    provider = RotationGenerateApplicationContextProvider(
        static_context_service=static,  # type: ignore[arg-type]
        demand_policy_provider=policies,  # type: ignore[arg-type]
        role_evidence_composer=composer,  # type: ignore[arg-type]
    )
    page = _Page()

    context = provider.context_for(page)

    assert static.calls == [page.build]
    assert policies.calls == ["rockgrove_xalvakka"]
    assert context.evidence_inputs.demand_policies == (demand_policy,)
    assert context.evidence_inputs.evaluator_resolver is None
    assert context.evidence_inputs.scorecard_resolver is None
    assert context.evidence_inputs.resource is ResourceType.MAGICKA
    assert context.evidence_inputs.maximum_amount == 32123
    assert context.evidence_inputs.trigger_fraction == 0.35
    assert context.evidence_inputs.knowledge_gaps == ()
    assert context.role_evidence_composer is composer
    assert context.character_id == "magrat-id"


def test_missing_demand_policy_is_blocking_not_silently_empty() -> None:
    provider = RotationGenerateApplicationContextProvider(
        static_context_service=_StaticContextService(_StaticContext()),  # type: ignore[arg-type]
        demand_policy_provider=None,
    )

    context = provider.context_for(_Page())

    assert context.evidence_inputs.demand_policies == ()
    assert len(context.evidence_inputs.knowledge_gaps) == 1
    gap = context.evidence_inputs.knowledge_gaps[0]
    assert gap.blocking is True
    assert gap.key == "rockgrove_xalvakka.rotation_demand_policy"
    assert gap.consumers == ("rotation_maker",)


def test_explicit_empty_demand_policy_is_distinct_from_unknown_policy() -> None:
    policies = _PolicyProvider(())
    provider = RotationGenerateApplicationContextProvider(
        static_context_service=_StaticContextService(_StaticContext()),  # type: ignore[arg-type]
        demand_policy_provider=policies,  # type: ignore[arg-type]
    )

    context = provider.context_for(_Page())

    assert context.evidence_inputs.demand_policies == ()
    assert context.evidence_inputs.knowledge_gaps == ()


def test_live_context_requires_explicit_recovery_resource_and_trigger() -> None:
    provider = RotationGenerateApplicationContextProvider(
        static_context_service=_StaticContextService(_StaticContext()),  # type: ignore[arg-type]
        demand_policy_provider=_PolicyProvider(()),  # type: ignore[arg-type]
    )
    page = _Page()
    page.policy["resource"] = None

    try:
        provider.context_for(page)
    except ValueError as exc:
        assert "select Magicka or Stamina recovery" in str(exc)
    else:
        raise AssertionError("missing recovery resource should block canonical Generate")

    page.policy["resource"] = ResourceType.MAGICKA
    page.policy["trigger_fraction"] = None
    try:
        provider.context_for(page)
    except ValueError as exc:
        assert "set an explicit recovery trigger" in str(exc)
    else:
        raise AssertionError("missing recovery trigger should block canonical Generate")


def test_unresolved_static_context_blocks_instead_of_inventing_resource_maximum() -> None:
    provider = RotationGenerateApplicationContextProvider(
        static_context_service=_StaticContextService(
            _StaticContext(resolved=False, unresolved=("unknown gear effect",))
        ),  # type: ignore[arg-type]
        demand_policy_provider=_PolicyProvider(()),  # type: ignore[arg-type]
    )

    try:
        provider.context_for(_Page())
    except ValueError as exc:
        assert str(exc) == (
            "canonical static build evidence is unresolved: unknown gear effect"
        )
    else:
        raise AssertionError("unresolved static build context should fail closed")
