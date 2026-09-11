from types import SimpleNamespace

import pytest

from ui.rotation_canonical_cadence_orchestration_support import (
    RotationCanonicalCadenceOrchestrationSupport,
)


class _CanonicalCandidates:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(candidate_result="canonical-application")

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _CanonicalRender:
    def __init__(self, evidence) -> None:
        self.evidence = evidence
        self.calls = []

    def build(self, application):
        self.calls.append(application)
        return self.evidence


class _CadenceRunner:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(final_plan="cadence-plan", final_sustain="cadence-sustain")

    def run(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _CadenceRender:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(
            plan="cadence-plan",
            sustain_projection="cadence-sustain",
            duration_evidence="cadence-duration",
            report="cadence-report",
        )

    def build(self, run):
        self.calls.append(run)
        return self.result


def _bundle(*, ready=True):
    blocking = () if ready else (
        SimpleNamespace(summary="target state missing", needed_evidence="review encounter target windows"),
    )
    return SimpleNamespace(
        ready=ready,
        unresolved=() if ready else ("support window unresolved",),
        blocking_knowledge_gaps=blocking,
        evaluator_resolver="evaluator",
        scorecard_resolver="scorecard",
        resource="magicka",
        maximum_amount=32000,
        trigger_fraction=0.35,
        restoration_resolver="restoration",
        demands=("demand",),
        options=("option",),
        wait_decision_factory="wait",
        requirements=("requirement",),
        passives=("passive",),
        reserve_assessment_resolver="reserve",
        max_iterations=6,
        baseline_id="baseline",
        coverage_report="coverage",
    )


def _support(*, canonical_evidence=None, runner=None):
    canonical = _CanonicalCandidates()
    render = _CanonicalRender(canonical_evidence)
    cadence_runner = runner or _CadenceRunner()
    cadence_render = _CadenceRender()
    support = RotationCanonicalCadenceOrchestrationSupport(
        canonical_candidates=canonical,
        canonical_render=render,
        cadence_runner=cadence_runner,
        cadence_render=cadence_render,
    )
    return support, canonical, render, cadence_runner, cadence_render


def test_rejects_unready_bundle_before_any_generation_or_rendering() -> None:
    support, canonical, render, cadence_runner, cadence_render = _support()

    with pytest.raises(ValueError, match="ready evidence bundle.*support window unresolved"):
        support.run(
            player_build=object(),  # type: ignore[arg-type]
            generation_request=object(),  # type: ignore[arg-type]
            evidence_bundle=_bundle(ready=False),  # type: ignore[arg-type]
        )

    assert canonical.calls == []
    assert render.calls == []
    assert cadence_runner.calls == []
    assert cadence_render.calls == []


def test_without_cadence_obligations_returns_selected_canonical_result_unchanged() -> None:
    canonical_evidence = SimpleNamespace(
        plan="canonical-plan",
        sustain_projection="canonical-sustain",
    )
    support, canonical, render, cadence_runner, cadence_render = _support(
        canonical_evidence=canonical_evidence
    )
    bundle = _bundle()
    build = object()
    request = object()
    role_evidence = object()

    result = support.run(
        player_build=build,  # type: ignore[arg-type]
        generation_request=request,  # type: ignore[arg-type]
        evidence_bundle=bundle,  # type: ignore[arg-type]
        role_evidence=role_evidence,  # type: ignore[arg-type]
        character_id="magrat-id",
    )

    assert result.canonical_result is canonical.result
    assert result.canonical_evidence is canonical_evidence
    assert result.cadence_run is None
    assert result.cadence_evidence is None
    assert result.cadence_applied is False
    assert result.final_plan == "canonical-plan"
    assert result.final_sustain == "canonical-sustain"
    assert cadence_runner.calls == []
    assert cadence_render.calls == []

    call = canonical.calls[0]
    assert call["player_build"] is build
    assert call["generation_request"] is request
    assert call["evaluator_resolver"] == "evaluator"
    assert call["scorecard_resolver"] == "scorecard"
    assert call["role_evidence"] is role_evidence
    assert call["demands"] == ("demand",)
    assert call["options"] == ("option",)
    assert call["requirements"] == ("requirement",)
    assert call["passives"] == ("passive",)
    assert call["character_id"] == "magrat-id"
    assert call["coverage_report"] == "coverage"


def test_legacy_cadence_orchestration_forwards_no_role_evidence() -> None:
    canonical_evidence = SimpleNamespace(
        plan="canonical-plan",
        sustain_projection="canonical-sustain",
    )
    support, canonical, _, _, _ = _support(canonical_evidence=canonical_evidence)

    support.run(
        player_build=object(),  # type: ignore[arg-type]
        generation_request=object(),  # type: ignore[arg-type]
        evidence_bundle=_bundle(),  # type: ignore[arg-type]
    )

    assert canonical.calls[0]["role_evidence"] is None


def test_unselectable_canonical_result_never_starts_cadence_progression() -> None:
    support, _, _, cadence_runner, cadence_render = _support(canonical_evidence=None)

    result = support.run(
        player_build=object(),  # type: ignore[arg-type]
        generation_request=object(),  # type: ignore[arg-type]
        evidence_bundle=_bundle(),  # type: ignore[arg-type]
        cadence_obligations=(object(),),  # type: ignore[arg-type]
    )

    assert result.final_plan is None
    assert result.final_sustain is None
    assert result.cadence_applied is False
    assert cadence_runner.calls == []
    assert cadence_render.calls == []


def test_cadence_progression_starts_from_final_canonical_plan_and_forwards_bundle_evidence() -> None:
    canonical_evidence = SimpleNamespace(
        plan="final-canonical-plan",
        sustain_projection="final-canonical-sustain",
    )
    support, _, _, cadence_runner, cadence_render = _support(
        canonical_evidence=canonical_evidence
    )
    obligation = object()
    priorities = object()
    evaluation_context = object()

    result = support.run(
        player_build="saved-build",  # type: ignore[arg-type]
        generation_request=object(),  # type: ignore[arg-type]
        evidence_bundle=_bundle(),  # type: ignore[arg-type]
        cadence_obligations=(obligation,),  # type: ignore[arg-type]
        cadence_priorities=priorities,  # type: ignore[arg-type]
        cadence_evaluation_context=evaluation_context,  # type: ignore[arg-type]
        cadence_max_iterations=5,
        character_id="magrat-id",
    )

    assert len(cadence_runner.calls) == 1
    call = cadence_runner.calls[0]
    assert call["build"] == "saved-build"
    assert call["seed_plan"] == "final-canonical-plan"
    assert call["seed_sustain"] == "final-canonical-sustain"
    assert call["obligations"] == (obligation,)
    assert call["max_iterations"] == 5
    assert call["priorities"] is priorities
    assert call["evaluation_context"] is evaluation_context
    assert call["effect_uptime_requirements"] == ("requirement",)
    assert call["passives"] == ("passive",)
    assert call["character_id"] == "magrat-id"

    assert cadence_render.calls == [cadence_runner.result]
    assert result.cadence_run is cadence_runner.result
    assert result.cadence_evidence is cadence_render.result
    assert result.cadence_applied is True
    assert result.final_plan == "cadence-plan"
    assert result.final_sustain == "cadence-sustain"


def test_default_constructor_composes_production_cadence_runner() -> None:
    support = RotationCanonicalCadenceOrchestrationSupport(
        canonical_candidates=_CanonicalCandidates(),
        canonical_render=_CanonicalRender(None),
        cadence_render=_CadenceRender(),
    )

    assert support.cadence_runner is not None
