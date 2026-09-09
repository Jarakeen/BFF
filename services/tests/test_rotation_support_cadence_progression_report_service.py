from types import SimpleNamespace

import pytest

from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_support_cadence_progression_report_service import (
    RotationSupportCadenceProgressionReportService,
)
from services.rotation_support_cadence_progression_runner_service import (
    RotationSupportCadenceProgressionRun,
    RotationSupportCadenceProgressionStopReason,
)


def _plan(name: str) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name=name,
        duration_seconds=30.0,
        actions=(),
    )


def _step(
    *,
    seed_name: str,
    candidate_count: int,
    tiers: tuple[RotationCandidateTier, ...],
    promoted_id: str | None = None,
    rationale: str = "target cadence preserves the explicit uptime floor",
    reasons: tuple[str, ...] = ("eligible candidate",),
    unresolved: tuple[str, ...] = (),
):
    recommended = None
    if promoted_id is not None:
        recommended = SimpleNamespace(
            candidate_id=promoted_id,
            rationale=rationale,
            reasons=reasons,
        )
    return SimpleNamespace(
        seed_plan=_plan(seed_name),
        neighborhood=SimpleNamespace(candidates=tuple(object() for _ in range(candidate_count))),
        ranking=tuple(SimpleNamespace(tier=tier) for tier in tiers),
        recommendation=SimpleNamespace(recommended=recommended),
        promoted_candidate_id=promoted_id,
        advanced=promoted_id is not None,
        unresolved=unresolved,
    )


def _run(*, steps, stop_reason, unresolved=()):
    initial = _plan("Seed")
    final = _plan("Final")
    run = RotationSupportCadenceProgressionRun(
        initial_plan=initial,
        initial_sustain=object(),  # type: ignore[arg-type]
        final_plan=final,
        final_sustain=object(),  # type: ignore[arg-type]
        steps=tuple(steps),  # type: ignore[arg-type]
        stop_reason=stop_reason,
        max_iterations=8,
    )
    if unresolved:
        run = SimpleNamespace(
            initial_plan=initial,
            final_plan=final,
            iterations=len(steps),
            advanced_steps=sum(1 for step in steps if step.advanced),
            steps=tuple(steps),
            stop_reason=stop_reason,
            unresolved=tuple(unresolved),
        )
    return run


def test_report_exposes_promoted_rationale_reasons_and_candidate_counts() -> None:
    step = _step(
        seed_name="DF Healer",
        candidate_count=3,
        tiers=(
            RotationCandidateTier.ELIGIBLE,
            RotationCandidateTier.INELIGIBLE,
            RotationCandidateTier.ELIGIBLE,
        ),
        promoted_id="major_courage:skill:target_floor",
        rationale="longest cadence that still meets the uptime target",
        reasons=("sustain improved", "uptime obligation satisfied"),
    )

    report = RotationSupportCadenceProgressionReportService().build(
        _run(
            steps=(step,),
            stop_reason=RotationSupportCadenceProgressionStopReason.MAX_ITERATIONS,
        )
    )

    item = report.steps[0]
    assert item.iteration == 1
    assert item.seed_build_name == "DF Healer"
    assert item.candidate_count == 3
    assert item.eligible_candidate_count == 2
    assert item.ineligible_candidate_count == 1
    assert item.promoted_candidate_id == "major_courage:skill:target_floor"
    assert item.promoted_rationale == "longest cadence that still meets the uptime target"
    assert item.promoted_reasons == ("sustain improved", "uptime obligation satisfied")
    assert item.advanced is True
    assert report.changed is True


def test_no_promotion_step_reports_no_promoted_explanation() -> None:
    step = _step(
        seed_name="DF Healer",
        candidate_count=2,
        tiers=(RotationCandidateTier.INELIGIBLE, RotationCandidateTier.INELIGIBLE),
    )

    report = RotationSupportCadenceProgressionReportService().build(
        _run(
            steps=(step,),
            stop_reason=RotationSupportCadenceProgressionStopReason.NO_PROMOTION,
        )
    )

    item = report.steps[0]
    assert item.promoted_candidate_id is None
    assert item.promoted_rationale is None
    assert item.promoted_reasons == ()
    assert item.eligible_candidate_count == 0
    assert report.stop_summary == (
        "No eligible local cadence candidate improved the accepted rotation."
    )
    assert report.changed is False


@pytest.mark.parametrize(
    ("reason", "expected"),
    (
        (
            RotationSupportCadenceProgressionStopReason.REPEATED_PLAN,
            "The next promoted candidate repeated an already accepted executable schedule.",
        ),
        (
            RotationSupportCadenceProgressionStopReason.MAX_ITERATIONS,
            "The configured progression iteration limit was reached.",
        ),
    ),
)
def test_stop_reason_is_explained_without_reinterpreting_it(reason, expected) -> None:
    report = RotationSupportCadenceProgressionReportService().build(
        _run(steps=(), stop_reason=reason)
    )

    assert report.stop_reason is reason
    assert report.stop_summary == expected


def test_run_unresolved_evidence_is_preserved_verbatim() -> None:
    unresolved = (
        "major_brittle: duration evidence missing",
        "target legality unresolved",
    )
    report = RotationSupportCadenceProgressionReportService().build(
        _run(
            steps=(),
            stop_reason=RotationSupportCadenceProgressionStopReason.NO_PROMOTION,
            unresolved=unresolved,
        )
    )

    assert report.unresolved == unresolved


def test_advanced_step_must_match_its_recommendation_identity() -> None:
    step = _step(
        seed_name="Seed",
        candidate_count=1,
        tiers=(RotationCandidateTier.ELIGIBLE,),
        promoted_id="candidate-a",
    )
    step.recommendation.recommended.candidate_id = "candidate-b"

    with pytest.raises(ValueError, match="does not match recommendation"):
        RotationSupportCadenceProgressionReportService().build(
            _run(
                steps=(step,),
                stop_reason=RotationSupportCadenceProgressionStopReason.MAX_ITERATIONS,
            )
        )
