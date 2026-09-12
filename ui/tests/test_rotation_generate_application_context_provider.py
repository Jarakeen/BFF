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
    def __init__(self, clock=(), threshold=(), blockers=()) -> None:
        self.clock = clock
        self.threshold = threshold
        self.blockers = blockers
        self.calls = []

    def policies_for(self, encounter_id):
        self.calls.append(("clock", encounter_id))
        return self.clock

    def threshold_policies_for(self, encounter_id):
        self.calls.append(("threshold", encounter_id))
        return self.threshold

    def review_blockers_for(self, encounter_id):
        self.calls.append(("blockers", encounter_id))
        return self.blockers


class _Page:
    def __init__(self) -> None:
        self.build = SimpleNamespace(Role="Healer")
        self.encounter_id = "rockgrove_xalvakka"
        self.policy = {
            "resource": ResourceType.MAGICKA,
            "trigger_fraction": 0.35,
        }
        self.threshold_policy = {
            "difficulty": None,
            "raid_dps": None,
        }

    def _selected_build(self):
        return self.build

    def selected_encounter_id(self):
        return self.encounter_id

    def canonical_recovery_policy(self):
        return dict(self.policy)

    def canonical_threshold_projection_policy(self):
        return dict(self.threshold_policy)


def test_live_context_uses_exact_build_encounter_explicit_policy_and_static_maximum() -> None:
    static = _StaticContextService(_StaticContext())
    demand_policy = object()
    policies = _PolicyProvider(clock=(demand_policy,))
    composer = object()
    provider = RotationGenerateApplicationContextProvider(
        static_context_service=static,  # type: ignore[arg-type]
        demand_policy_provider=policies,  # type: ignore[arg-type]
        role_evidence_composer=composer,  # type: ignore[arg-type]
    )
    page = _Page()

    context = provider.context_for(page)

    assert static.calls == [page.build]
    assert policies.calls == [
        ("clock", "rockgrove_xalvakka"),
        ("threshold", "rockgrove_xalvakka"),
        ("blockers", "rockgrove_xalvakka"),
    ]
    assert context.evidence_inputs.demand_policies == (demand_policy,)
    assert context.evidence_inputs.threshold_demand_policies == ()
    assert context.evidence_inputs.threshold_damage_segments == ()
    assert context.evidence_inputs.difficulty == ""
    assert context.evidence_inputs.evaluator_resolver is None
    assert context.evidence_inputs.scorecard_resolver is None
    assert context.evidence_inputs.resource is ResourceType.MAGICKA
    assert context.evidence_inputs.maximum_amount == 32123
    assert context.evidence_inputs.trigger_fraction == 0.35
    assert context.evidence_inputs.knowledge_gaps == ()
    assert context.role_evidence_composer is composer
    assert context.character_id == "magrat-id"


def test_threshold_policy_requires_explicit_difficulty_and_raid_dps() -> None:
    threshold_policy = object()
    provider = RotationGenerateApplicationContextProvider(
        static_context_service=_StaticContextService(_StaticContext()),  # type: ignore[arg-type]
        demand_policy_provider=_PolicyProvider(threshold=(threshold_policy,)),  # type: ignore[arg-type]
    )
    page = _Page()

    try:
        provider.context_for(page)
    except ValueError as exc:
        assert "select Normal, Veteran, or Hardmode" in str(exc)
    else:
        raise AssertionError("threshold policy without difficulty should block Generate")

    page.threshold_policy["difficulty"] = "hardmode"
    try:
        provider.context_for(page)
    except ValueError as exc:
        assert "set explicit raid DPS" in str(exc)
    else:
        raise AssertionError("threshold policy without raid DPS should block Generate")

    page.threshold_policy["raid_dps"] = 2_000_000.0
    context = provider.context_for(page)
    assert context.evidence_inputs.threshold_demand_policies == (threshold_policy,)
    assert context.evidence_inputs.difficulty == "hardmode"
    assert len(context.evidence_inputs.threshold_damage_segments) == 1
    segment = context.evidence_inputs.threshold_damage_segments[0]
    assert segment.damage_per_second == 2_000_000.0
    assert "explicit Rotation Builder" in segment.source


def test_missing_demand_policy_is_blocking_not_silently_empty() -> None:
    provider = RotationGenerateApplicationContextProvider(
        static_context_service=_StaticContextService(_StaticContext()),  # type: ignore[arg-type]
        demand_policy_provider=_PolicyProvider(clock=None, threshold=None),  # type: ignore[arg-type]
    )

    context = provider.context_for(_Page())

    assert context.evidence_inputs.demand_policies == ()
    assert context.evidence_inputs.threshold_demand_policies == ()
    assert len(context.evidence_inputs.knowledge_gaps) == 1
    gap = context.evidence_inputs.knowledge_gaps[0]
    assert gap.blocking is True
    assert gap.key == "rockgrove_xalvakka.rotation_demand_policy"
    assert gap.consumers == ("rotation_maker",)


def test_explicit_empty_demand_policy_is_distinct_from_unknown_policy() -> None:
    provider = RotationGenerateApplicationContextProvider(
        static_context_service=_StaticContextService(_StaticContext()),  # type: ignore[arg-type]
        demand_policy_provider=_PolicyProvider(clock=(), threshold=()),  # type: ignore[arg-type]
    )

    context = provider.context_for(_Page())

    assert context.evidence_inputs.demand_policies == ()
    assert context.evidence_inputs.threshold_demand_policies == ()
    assert context.evidence_inputs.knowledge_gaps == ()


def test_reviewed_encounter_with_policy_blocker_surfaces_specific_gap() -> None:
    blocker = SimpleNamespace(
        key="phase_2_healer_demand_policy",
        summary="Phase 2 anchor is reviewed but healer demand policy is not.",
        needed_evidence="Approve lead, window, pattern, and target count.",
        source_context="reviewed Xalvakka Phase 2 evidence",
    )
    provider = RotationGenerateApplicationContextProvider(
        static_context_service=_StaticContextService(_StaticContext()),  # type: ignore[arg-type]
        demand_policy_provider=_PolicyProvider(
            clock=(), threshold=(), blockers=(blocker,)
        ),  # type: ignore[arg-type]
    )

    context = provider.context_for(_Page())

    assert context.evidence_inputs.demand_policies == ()
    assert context.evidence_inputs.threshold_demand_policies == ()
    assert len(context.evidence_inputs.knowledge_gaps) == 1
    gap = context.evidence_inputs.knowledge_gaps[0]
    assert gap.blocking is True
    assert gap.key == "rockgrove_xalvakka.phase_2_healer_demand_policy"
    assert gap.summary == blocker.summary
    assert gap.needed_evidence == blocker.needed_evidence
    assert gap.source_context == blocker.source_context


def test_live_context_requires_explicit_recovery_resource_and_trigger() -> None:
    provider = RotationGenerateApplicationContextProvider(
        static_context_service=_StaticContextService(_StaticContext()),  # type: ignore[arg-type]
        demand_policy_provider=_PolicyProvider(),  # type: ignore[arg-type]
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
        demand_policy_provider=_PolicyProvider(),  # type: ignore[arg-type]
    )

    try:
        provider.context_for(_Page())
    except ValueError as exc:
        assert str(exc) == (
            "canonical static build evidence is unresolved: unknown gear effect"
        )
    else:
        raise AssertionError("unresolved static build context should fail closed")
