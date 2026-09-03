from minmax.build_candidate import BuildCandidate, BuildChange
from minmax.build_candidate_comparison import (
    BuildCandidateComparison,
    CandidateConstraint,
    ConstraintStatus,
)
from minmax.evaluation_objective import EvaluationObjective
from models.build_model import PlayerBuild
from tools.audit_phase12_saved_dd_candidates import _print_dd_recommendation


def _comparison(*, unresolved=()):
    candidate = BuildCandidate.from_build(
        character_id="magrat",
        baseline_build_id="df-healer",
        candidate_id="mundus:the-atronach",
        candidate_build=PlayerBuild(
            Name="Magrat",
            BuildName="DF Healer",
            Mundus="The Atronach",
        ),
        changes=(
            BuildChange.from_values(
                path="Mundus",
                before="The Ritual",
                after="The Atronach",
                source="phase12:test",
            ),
        ),
        candidate_source="phase12:test",
    )
    return BuildCandidateComparison(
        candidate=candidate,
        objective=EvaluationObjective.DAMAGE,
        baseline_value=2091.396,
        candidate_value=2091.396,
        constraints=(
            CandidateConstraint(
                "magicka sustain",
                ConstraintStatus.REPAIRED,
                "Candidate repairs failed baseline magicka sustain.",
            ),
            CandidateConstraint(
                "capability_coverage",
                ConstraintStatus.PRESERVED,
                "Candidate preserves all resolved baseline capability identities.",
            ),
            CandidateConstraint(
                "provider_responsibility",
                ConstraintStatus.PRESERVED,
                "Candidate preserves every baseline primary provider responsibility.",
            ),
        ),
        unresolved=tuple(unresolved),
    )


def test_recommendation_prints_plain_summary_and_technical_evidence(capsys) -> None:
    _print_dd_recommendation(
        _comparison(),
        metric_name="canonical single-event expected damage",
        role_mismatch=True,
        provider_scope_evaluated=True,
    )

    output = capsys.readouterr().out
    assert "Recommendation: The Atronach" in output
    assert "In plain English:" in output
    assert "current build runs out of Magicka" in output
    assert "does not remove any resolved buffs, debuffs" in output
    assert "still handle the raid jobs" in output
    assert "does not show a damage increase" in output
    assert "only a diagnostic damage test on a non-DD build" in output
    assert "not your actual rotation DPS" in output

    assert "Technical evidence:" in output
    assert "Reason: hard-constraint repair" in output
    assert "Mundus: The Ritual -> The Atronach" in output
    assert "metric: canonical single-event expected damage" in output
    assert "magicka sustain: repaired" in output
    assert "capability_coverage: preserved" in output
    assert "provider_responsibility: preserved" in output
    assert "not rotation DPS or raid ceiling damage" in output
    assert "encounter-specific skill uptime is not modeled" in output
    assert "Phase 11 provider responsibilities were evaluated" in output
    assert "diagnostic role override only" in output


def test_recommendation_prints_unresolved_candidate_evidence(capsys) -> None:
    _print_dd_recommendation(
        _comparison(unresolved=("example unresolved assumption",)),
        metric_name="canonical single-event expected damage",
        role_mismatch=False,
        provider_scope_evaluated=False,
    )

    output = capsys.readouterr().out
    assert "Unresolved:" in output
    assert "example unresolved assumption" in output
    assert "provider responsibilities were not evaluated" in output
    assert "only a diagnostic damage test on a non-DD build" not in output
    assert "diagnostic role override only" not in output


def test_no_recommendation_remains_explicit(capsys) -> None:
    _print_dd_recommendation(
        None,
        metric_name="canonical single-event expected damage",
        role_mismatch=False,
        provider_scope_evaluated=False,
    )

    assert capsys.readouterr().out == "Recommendation: none.\n"
