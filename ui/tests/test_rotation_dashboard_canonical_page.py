from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from minmax.rotation_ability_priority import AbilityPriorityEntry
from models.build_model import PlayerBuild
from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage
from ui.rotation_generation_support import RotationGenerationRequest


def _build() -> PlayerBuild:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")
    build.FrontBarSkills = ["Combat Prayer", "", "", "", "", ""]
    return build


def _priorities() -> tuple[AbilityPriorityEntry, ...]:
    return (
        AbilityPriorityEntry(
            bar="front",
            slot=1,
            skill_name="Combat Prayer",
            priority=10,
        ),
    )


class _CanonicalCandidates:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(candidate_result="canonical-result")

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _CadenceCard:
    def __init__(self) -> None:
        self.clear_calls = 0

    def clear_report(self) -> None:
        self.clear_calls += 1


class _PageState:
    def __init__(self, *, build=None) -> None:
        self.build = _build() if build is None else build
        self.rotation_canonical_candidates = _CanonicalCandidates()
        self.last_canonical_candidate_result = None
        self.last_canonical_render_evidence = None
        self.last_cadence_progression_run = object()
        self.last_cadence_progression_render_evidence = object()
        self.cadence_progression_card = _CadenceCard()

    def _selected_build(self):
        return self.build

    def ability_priorities(self):
        return _priorities()

    def rotation_settings(self):
        return {
            "rotation_type": "Semi-static",
            "potion": "Essence of Spell Power",
            "potion_on_cooldown": True,
            "ultimate_bar": "front",
            "starting_ultimate": 125,
            "use_scheduled_combat_attacks_for_ultimate": True,
        }

    def canonical_generation_request(self):
        return CanonicalRotationDashboardPage.canonical_generation_request(self)

    def evaluate_canonical_candidates(self, **kwargs):
        return CanonicalRotationDashboardPage.evaluate_canonical_candidates(self, **kwargs)


class _RenderSupport:
    def __init__(self, evidence) -> None:
        self.evidence = evidence
        self.calls = []

    def build(self, result):
        self.calls.append(result)
        return self.evidence


class _Status:
    def __init__(self) -> None:
        self.warnings = []

    def warning(self, message: str) -> None:
        self.warnings.append(message)


class _DurationCard:
    def __init__(self) -> None:
        self.evidence = []

    def set_evidence(self, evidence) -> None:
        self.evidence.append(evidence)


class _RenderPageState:
    def __init__(self, evidence) -> None:
        self.rotation_canonical_render = _RenderSupport(evidence)
        self.last_canonical_candidate_result = SimpleNamespace(
            candidate_result="application-result"
        )
        self.last_canonical_render_evidence = None
        self.status = _Status()
        self.duration_evidence_card = _DurationCard()
        self.plans = []
        self.sustain = []

    def set_rotation_plan(self, plan) -> None:
        self.plans.append(plan)

    def set_sustain_projection(self, projection) -> None:
        self.sustain.append(projection)


def test_page_builds_candidate_generation_request_from_current_dashboard_state() -> None:
    page = _PageState()

    request = CanonicalRotationDashboardPage.canonical_generation_request(page)

    assert isinstance(request, RotationGenerationRequest)
    assert request.duration_seconds == 60.0
    assert request.rotation_type == "Semi-static"
    assert request.potion == "Essence of Spell Power"
    assert request.potion_on_cooldown is True
    assert request.ultimate_bar == "front"
    assert request.starting_ultimate == 125.0
    assert request.use_scheduled_combat_attacks_for_ultimate is True
    assert request.ability_priorities == _priorities()
    assert request.stabilize_recovery_heavies is False


def test_page_candidate_evaluation_forwards_explicit_evidence_and_records_result() -> None:
    page = _PageState()
    page.last_canonical_render_evidence = object()
    evaluator_resolver = object()
    scorecard_resolver = object()
    restoration_resolver = object()
    wait_factory = object()
    reserve_resolver = object()

    result = CanonicalRotationDashboardPage.evaluate_canonical_candidates(
        page,
        evaluator_resolver=evaluator_resolver,
        scorecard_resolver=scorecard_resolver,
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
        restoration_resolver=restoration_resolver,
        demands=(item for item in ("demand-a", "demand-b")),
        options=(item for item in ("option-a",)),
        wait_decision_factory=wait_factory,
        requirements=(item for item in ("major-brittle",)),
        passives=(item for item in ("class-passive", "armor-passive")),
        reserve_assessment_resolver=reserve_resolver,
        max_iterations=8,
        baseline_id="dashboard-baseline",
        character_id="magrat-id",
    )

    assert result is page.rotation_canonical_candidates.result
    assert page.last_canonical_candidate_result is result
    assert page.last_canonical_render_evidence is None
    assert page.last_cadence_progression_run is None
    assert page.last_cadence_progression_render_evidence is None
    assert page.cadence_progression_card.clear_calls == 1
    assert len(page.rotation_canonical_candidates.calls) == 1
    call = page.rotation_canonical_candidates.calls[0]
    assert call["player_build"] is page.build
    assert call["generation_request"].ability_priorities == _priorities()
    assert call["evaluator_resolver"] is evaluator_resolver
    assert call["scorecard_resolver"] is scorecard_resolver
    assert call["resource"] is ResourceType.MAGICKA
    assert call["maximum_amount"] == 32000
    assert call["trigger_fraction"] == 0.35
    assert call["restoration_resolver"] is restoration_resolver
    assert call["demands"] == ("demand-a", "demand-b")
    assert call["options"] == ("option-a",)
    assert call["wait_decision_factory"] is wait_factory
    assert call["requirements"] == ("major-brittle",)
    assert call["passives"] == ("class-passive", "armor-passive")
    assert call["reserve_assessment_resolver"] is reserve_resolver
    assert call["max_iterations"] == 8
    assert call["baseline_id"] == "dashboard-baseline"
    assert call["character_id"] == "magrat-id"


def test_page_candidate_evaluation_requires_selected_saved_build() -> None:
    page = _PageState()
    page.build = None

    with pytest.raises(ValueError, match="select a saved build"):
        CanonicalRotationDashboardPage.evaluate_canonical_candidates(
            page,
            evaluator_resolver=object(),
            scorecard_resolver=object(),
            resource=ResourceType.MAGICKA,
            maximum_amount=32000,
            trigger_fraction=0.35,
            restoration_resolver=object(),
        )

    assert page.rotation_canonical_candidates.calls == []


def test_page_consumes_ready_canonical_evidence_bundle_as_one_evaluation_input() -> None:
    page = _PageState()
    evaluator = object()
    scorecard = object()
    restoration = object()
    wait_factory = object()
    reserve = object()
    bundle = SimpleNamespace(
        ready=True,
        unresolved=(),
        evaluator_resolver=evaluator,
        scorecard_resolver=scorecard,
        resource=ResourceType.MAGICKA,
        maximum_amount=31500,
        trigger_fraction=0.4,
        restoration_resolver=restoration,
        demands=("encounter-demand",),
        options=("refresh-option",),
        wait_decision_factory=wait_factory,
        requirements=("effect-requirement",),
        passives=("class-passive", "armor-passive"),
        reserve_assessment_resolver=reserve,
        max_iterations=7,
        baseline_id="encounter-baseline",
    )

    result = CanonicalRotationDashboardPage.evaluate_canonical_evidence_bundle(
        page,
        bundle,
        character_id="magrat-id",
    )

    assert result is page.rotation_canonical_candidates.result
    call = page.rotation_canonical_candidates.calls[0]
    assert call["evaluator_resolver"] is evaluator
    assert call["scorecard_resolver"] is scorecard
    assert call["resource"] is ResourceType.MAGICKA
    assert call["maximum_amount"] == 31500
    assert call["trigger_fraction"] == 0.4
    assert call["restoration_resolver"] is restoration
    assert call["demands"] == ("encounter-demand",)
    assert call["options"] == ("refresh-option",)
    assert call["wait_decision_factory"] is wait_factory
    assert call["requirements"] == ("effect-requirement",)
    assert call["passives"] == ("class-passive", "armor-passive")
    assert call["reserve_assessment_resolver"] is reserve
    assert call["max_iterations"] == 7
    assert call["baseline_id"] == "encounter-baseline"
    assert call["character_id"] == "magrat-id"


def test_page_refuses_unresolved_canonical_evidence_bundle_before_generation() -> None:
    page = _PageState()
    bundle = SimpleNamespace(
        ready=False,
        unresolved=("required support window is not reviewed",),
    )

    with pytest.raises(ValueError, match="not ready.*not reviewed"):
        CanonicalRotationDashboardPage.evaluate_canonical_evidence_bundle(page, bundle)

    assert page.rotation_canonical_candidates.calls == []


def test_page_renders_plan_duration_and_sustain_from_one_final_evidence_bundle() -> None:
    evidence = SimpleNamespace(
        candidate_id="winner",
        plan=object(),
        duration_evidence=object(),
        sustain_projection=object(),
        effect_uptime_assessments=(object(),),
    )
    page = _RenderPageState(evidence)

    rendered = CanonicalRotationDashboardPage.apply_canonical_candidate_result(page)

    assert rendered is evidence
    assert page.last_canonical_render_evidence is evidence
    assert page.rotation_canonical_render.calls == ["application-result"]
    assert page.plans == [evidence.plan]
    assert page.duration_evidence_card.evidence == [evidence.duration_evidence]
    assert page.sustain == [evidence.sustain_projection]
    assert page.status.warnings == []


def test_page_does_not_replace_existing_display_when_no_candidate_is_selectable() -> None:
    page = _RenderPageState(None)

    rendered = CanonicalRotationDashboardPage.apply_canonical_candidate_result(page)

    assert rendered is None
    assert page.last_canonical_render_evidence is None
    assert page.plans == []
    assert page.duration_evidence_card.evidence == []
    assert page.sustain == []
    assert len(page.status.warnings) == 1
    assert "no selectable rotation" in page.status.warnings[0].casefold()


def test_page_requires_candidate_evaluation_before_rendering() -> None:
    page = _RenderPageState(None)
    page.last_canonical_candidate_result = None

    with pytest.raises(ValueError, match="no canonical candidate evaluation"):
        CanonicalRotationDashboardPage.apply_canonical_candidate_result(page)

    assert page.rotation_canonical_render.calls == []
