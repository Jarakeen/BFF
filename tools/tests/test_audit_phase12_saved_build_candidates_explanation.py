from minmax.build_candidate import BuildCandidate, BuildChange
from minmax.build_candidate_comparison import (
    BuildCandidateComparison,
    CandidateConstraint,
    ConstraintStatus,
)
from minmax.build_candidate_evaluator import CandidateRanking
from minmax.evaluation_objective import EvaluationObjective
from models.build_model import PlayerBuild
from tools.audit_phase12_saved_build_candidates import _print_recommendation


def _comparison() -> BuildCandidateComparison:
    candidate = BuildCandidate.from_build(
        character_id="magrat",
        baseline_build_id="df-healer",
        candidate_id="food:clockwork-citrus-filet",
        candidate_build=PlayerBuild(
            Name="Magrat",
            BuildName="DF Healer",
            Food="Clockwork Citrus Filet",
        ),
        changes=(
            BuildChange.from_values(
                path="Food",
                before="Witchmother's Potent Brew",
                after="Clockwork Citrus Filet",
                source="phase12:test",
            ),
        ),
        candidate_source="phase12:test",
    )
    return BuildCandidateComparison(
        candidate=candidate,
        objective=EvaluationObjective.HEALING,
        baseline_value=1000.0,
        candidate_value=1035.0,
        constraints=(
            CandidateConstraint(
                "magicka sustain",
                ConstraintStatus.PRESERVED,
                "Technical sustain evidence.",
            ),
            CandidateConstraint(
                "capability_coverage",
                ConstraintStatus.PRESERVED,
                "Technical capability evidence.",
            ),
        ),
    )


def test_bounded_recommendation_prints_plain_english_before_technical_evidence(capsys) -> None:
    comparison = _comparison()
    ranking = CandidateRanking(
        comparisons=(comparison,),
        ranked=(comparison,),
        recommended=comparison,
        recommended_ties=(comparison,),
    )

    _print_recommendation("Food", ranking)

    output = capsys.readouterr().out
    assert "Food recommendation: Food: Witchmother's Potent Brew -> Clockwork Citrus Filet" in output
    assert "Plain English:" in output
    assert "passes the required checks and improves the modeled result" in output
    assert "Change Food from Witchmother's Potent Brew to Clockwork Citrus Filet" in output
    assert "keeps resource sustain at least as safe" in output
    assert "buffs, debuffs" in output
    assert "not actual HPS" in output
    assert "provider assignments are not evaluated" in output
    assert "Technical evidence:" in output
    assert "magicka sustain: preserved: Technical sustain evidence." in output
    assert output.index("Plain English:") < output.index("Technical evidence:")
