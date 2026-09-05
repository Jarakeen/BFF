from services.comp_builder_build_candidates import CompBuildCandidate
from services.comp_builder_composition_style import CompCompositionStyle
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


def test_mapped_provider_requirement_blocks_higher_scoring_non_provider() -> None:
    raw = _candidate("raw", player="Raw", score=500)
    provider = _candidate("provider", player="Provider", score=100)

    result = optimize_comp_team_candidates(
        pools=(
            CompTeamCandidatePool(
                "Healer 1",
                (raw, provider),
                required_provider_ids=("force",),
            ),
        ),
        provider_ids_by_candidate={
            "raw": (),
            "provider": ("force",),
        },
    )

    assert result.assignments[0].candidate.candidate_id == "provider"
    assert result.provider_blocked_slots == ()


def test_mapped_provider_requirement_leaves_chair_open_when_no_candidate_proves_it() -> None:
    raw = _candidate("raw", player="Raw", score=500)

    result = optimize_comp_team_candidates(
        pools=(
            CompTeamCandidatePool(
                "Healer 1",
                (raw,),
                required_provider_ids=("force",),
            ),
        ),
        provider_ids_by_candidate={"raw": ()},
    )

    assert result.assignments[0].candidate is None
    assert result.provider_blocked_slots == ("Healer 1",)
    assert result.unresolved_slots == ("Healer 1",)


def test_raid_wide_provider_requirement_prefers_team_coverage_over_relevance() -> None:
    raw = _candidate("raw", player="Raw", score=500)
    courage = _candidate("courage", player="Courage", score=100)
    second = _candidate("second", player="Second", score=90)

    result = optimize_comp_team_candidates(
        pools=(
            CompTeamCandidatePool("Healer 1", (raw, courage)),
            CompTeamCandidatePool("Healer 2", (second,)),
        ),
        provider_ids_by_candidate={
            "raw": (),
            "courage": ("major_courage",),
            "second": (),
        },
        required_team_provider_ids=("major_courage",),
    )

    selected = {row.slot_name: row.candidate.candidate_id for row in result.assignments}
    assert selected == {"Healer 1": "courage", "Healer 2": "second"}
    assert result.uncovered_team_provider_ids == ()


def test_raid_wide_provider_requirement_respects_precovered_manual_assignment() -> None:
    raw = _candidate("raw", player="Raw", score=500)
    courage = _candidate("courage", player="Courage", score=100)

    result = optimize_comp_team_candidates(
        pools=(CompTeamCandidatePool("Healer 2", (raw, courage)),),
        provider_ids_by_candidate={
            "raw": (),
            "courage": ("major_courage",),
        },
        required_team_provider_ids=("major_courage",),
        already_covered_team_provider_ids=("major_courage",),
    )

    assert result.assignments[0].candidate.candidate_id == "raw"
    assert result.uncovered_team_provider_ids == ()


def test_impossible_raid_wide_provider_requirement_is_reported_without_emptying_roster() -> None:
    first = _candidate("first", player="First", score=100)
    second = _candidate("second", player="Second", score=90)

    result = optimize_comp_team_candidates(
        pools=(
            CompTeamCandidatePool("Healer 1", (first,)),
            CompTeamCandidatePool("Healer 2", (second,)),
        ),
        provider_ids_by_candidate={"first": (), "second": ()},
        required_team_provider_ids=("major_courage",),
    )

    assert result.applied_count == 2
    assert result.uncovered_team_provider_ids == ("major_courage",)


def test_off_meta_style_can_prefer_evidence_backed_novel_candidate() -> None:
    conventional = _candidate("conventional", player="Conventional", score=120)
    unusual = _candidate("unusual", player="Unusual", score=100)

    result = optimize_comp_team_candidates(
        pools=(CompTeamCandidatePool("Healer 1", (conventional, unusual)),),
        composition_style=CompCompositionStyle.OFF_META,
        novelty_by_candidate={"unusual": 25.0},
    )

    assert result.assignments[0].candidate.candidate_id == "unusual"


def test_off_meta_style_never_trades_required_provider_coverage_for_novelty() -> None:
    provider = _candidate("provider", player="Provider", score=100)
    unusual = _candidate("unusual", player="Unusual", score=100)

    result = optimize_comp_team_candidates(
        pools=(CompTeamCandidatePool("Healer 1", (provider, unusual)),),
        provider_ids_by_candidate={
            "provider": ("major_courage",),
            "unusual": (),
        },
        required_team_provider_ids=("major_courage",),
        composition_style=CompCompositionStyle.OFF_META,
        novelty_by_candidate={"unusual": 10000.0},
    )

    assert result.assignments[0].candidate.candidate_id == "provider"
    assert result.uncovered_team_provider_ids == ()


def test_off_meta_style_never_prefers_novelty_over_filling_a_chair() -> None:
    usable = _candidate("usable", player="Usable", score=1)

    result = optimize_comp_team_candidates(
        pools=(CompTeamCandidatePool("Healer 1", (usable,)),),
        composition_style=CompCompositionStyle.OFF_META,
        novelty_by_candidate={},
    )

    assert result.assignments[0].candidate.candidate_id == "usable"
    assert result.applied_count == 1
