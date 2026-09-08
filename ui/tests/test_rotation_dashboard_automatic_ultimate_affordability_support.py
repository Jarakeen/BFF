from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_ability_priority import AbilityPriorityEntry
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.ultimate_resource_timeline import UltimateGenerationEvent, UltimateSpendRule
from models.build_model import PlayerBuild
from ui.rotation_dashboard_canonical_candidate_support import (
    RotationDashboardCanonicalCandidateSupport,
)
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationResult
from ui.rotation_ultimate_affordability_candidate_support import (
    RotationUltimateAffordabilityCandidateSupport,
)


def _build() -> PlayerBuild:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")
    build.FrontBarSkills = ["Combat Prayer", "", "", "", "", "Aggressive Horn"]
    return build


def _request(**changes) -> RotationGenerationRequest:
    values = dict(
        duration_seconds=60.0,
        ultimate_bar="front",
        starting_ultimate=50.0,
        ability_priorities=(
            AbilityPriorityEntry(
                bar="front",
                slot=1,
                skill_name="Combat Prayer",
                priority=10,
            ),
        ),
    )
    values.update(changes)
    return RotationGenerationRequest(**values)


class _Generation:
    def __init__(self, projection) -> None:
        self.calls = []
        self.result = RotationGenerationResult(
            plan=RotationPlan(
                character_name="Magrat",
                build_name="DF Healer",
                duration_seconds=60.0,
                actions=(),
            ),
            duration_evidence=SimpleNamespace(summary="seed"),
            ultimate_projection=projection,
        )

    def generate_with_evidence(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _Canonical:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(validation="ok")

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def _run(generation, canonical, *, request=None):
    support = RotationDashboardCanonicalCandidateSupport(
        generation=generation,
        canonical_candidates=canonical,
    )
    return support.run_effects(
        player_build=_build(),
        generation_request=request or _request(),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
    )


def test_dashboard_default_composes_final_ultimate_affordability_support() -> None:
    support = RotationDashboardCanonicalCandidateSupport(generation=_Generation(None))

    assert isinstance(
        support.canonical_candidates,
        RotationUltimateAffordabilityCandidateSupport,
    )


def test_dashboard_builds_final_affordability_requirement_from_seed_projection_evidence() -> None:
    event = UltimateGenerationEvent(10.0, 200.0, "verified generation")
    projection = SimpleNamespace(
        spend_rules=(UltimateSpendRule("Aggressive Horn", 250.0),),
        generation_events=(event,),
    )
    generation = _Generation(projection)
    canonical = _Canonical()

    _run(generation, canonical)

    requirement = canonical.calls[0]["ultimate_affordability_requirement"]
    assert requirement.starting_amount == 50.0
    assert requirement.spend_rules == projection.spend_rules
    assert requirement.generation_events == (event,)


def test_dashboard_does_not_invent_affordability_requirement_without_resolved_spend() -> None:
    projection = SimpleNamespace(spend_rules=(), generation_events=())
    generation = _Generation(projection)
    canonical = _Canonical()

    _run(generation, canonical)

    assert "ultimate_affordability_requirement" not in canonical.calls[0]


def test_dashboard_recomputes_attack_generation_from_final_candidate_plan() -> None:
    seed_attack_event = UltimateGenerationEvent(10.0, 3.0, "stale seed attack generation")
    projection = SimpleNamespace(
        spend_rules=(UltimateSpendRule("Aggressive Horn", 250.0),),
        generation_events=(seed_attack_event,),
    )
    generation = _Generation(projection)
    canonical = _Canonical()

    _run(
        generation,
        canonical,
        request=_request(use_scheduled_combat_attacks_for_ultimate=True),
    )

    call = canonical.calls[0]
    requirement = call["ultimate_affordability_requirement"]
    assert requirement.starting_amount == 50.0
    assert requirement.spend_rules == projection.spend_rules
    assert requirement.generation_events == ()

    resolver = call["ultimate_generation_event_resolver"]
    candidate_plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=12.0,
        actions=(
            RotationAction(2.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
        ),
    )
    events = resolver(candidate_plan)

    assert events
    assert events[0].time_seconds == 3.0
    assert events[0].amount == 3.0
    assert all(event.source == "base combat Ultimate generation" for event in events)
    assert seed_attack_event not in events
