from services.comp_builder_build_candidates import CompBuildCandidate
from services.comp_builder_team_candidate_optimizer import (
    CompTeamCandidatePool,
    optimize_comp_team_candidates,
)


def _candidate(
    candidate_id: str,
    *,
    player: str,
    score: float,
    source_kind: str = "saved_build",
) -> CompBuildCandidate:
    return CompBuildCandidate(
        candidate_id=candidate_id,
        name=candidate_id,
        source_kind=source_kind,
        source_name=player,
        source_url="",
        eso_class="Warden",
        role="Healer",
        gear_sets=(),
        skills=(),
        mundus="",
        complete_build=source_kind == "saved_build",
        unresolved=(),
        score=score,
        score_reasons=(),
    )


def test_optimizer_places_shared_saved_player_where_team_assignment_is_stronger() -> None:
    magrat_h1 = _candidate("magrat-h1", player="Magrat", score=100)
    magrat_h2 = _candidate("magrat-h2", player="Magrat", score=120)
    other_h1 = _candidate("other-h1", player="Other", score=99)
    reference_h2 = _candidate(
        "reference-h2",
        player="BTV Tools",
        score=500,
        source_kind="reference_template",
    )

    result = optimize_comp_team_candidates(
        pools=(
            CompTeamCandidatePool("Healer 1", (magrat_h1, other_h1)),
            CompTeamCandidatePool("Healer 2", (magrat_h2, reference_h2)),
        )
    )

    selected = {row.slot_name: row.candidate for row in result.assignments}
    assert selected["Healer 1"].candidate_id == "other-h1"
    assert selected["Healer 2"].candidate_id == "magrat-h2"
    assert result.applied_count == 2


def test_optimizer_respects_saved_players_already_used_by_manual_chairs() -> None:
    magrat = _candidate("magrat", player="Magrat", score=200)
    other = _candidate("other", player="Other", score=100)

    result = optimize_comp_team_candidates(
        pools=(CompTeamCandidatePool("Healer 2", (magrat, other)),),
        already_used_saved_players=("Magrat",),
    )

    assert result.assignments[0].candidate.candidate_id == "other"


def test_reference_templates_do_not_consume_a_player_identity() -> None:
    reference = _candidate(
        "reference",
        player="BTV Tools",
        score=50,
        source_kind="reference_template",
    )

    result = optimize_comp_team_candidates(
        pools=(
            CompTeamCandidatePool("DD 1", (reference,)),
            CompTeamCandidatePool("DD 2", (reference,)),
        )
    )

    assert [row.candidate.candidate_id for row in result.assignments] == [
        "reference",
        "reference",
    ]
