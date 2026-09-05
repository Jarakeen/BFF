from services.comp_builder_build_candidates import CompBuildCandidate
from services.comp_builder_strategy_evidence import evaluate_provider_redistribution_strategy


def _candidate(candidate_id: str, *, role: str = "Healer") -> CompBuildCandidate:
    return CompBuildCandidate(
        candidate_id=candidate_id,
        name=candidate_id,
        source_kind="reference_template",
        source_name="test",
        source_url="",
        eso_class="Warden",
        role=role,
        gear_sets=(),
        skills=(),
        mundus="",
        complete_build=True,
        unresolved=(),
        score=100.0,
        score_reasons=(),
    )


def test_strategy_scores_rare_provider_ownership_within_role() -> None:
    candidates = tuple(_candidate(name) for name in ("a", "b", "c", "d"))
    result = evaluate_provider_redistribution_strategy(
        candidates,
        provider_ids_by_candidate={
            "a": ("major_courage",),
            "b": (),
            "c": (),
            "d": (),
        },
    )

    assert result.score_by_candidate["a"] == 75.0
    assert result.score_by_candidate["b"] == 0.0
    assert "1/4 eligible healer" in " | ".join(result.evidence[0].reasons)


def test_strategy_does_not_credit_unknown_provider_evidence() -> None:
    candidates = tuple(_candidate(name) for name in ("a", "b", "c"))
    result = evaluate_provider_redistribution_strategy(
        candidates,
        provider_ids_by_candidate={"a": (), "b": (), "c": ()},
    )

    assert result.score_by_candidate == {"a": 0.0, "b": 0.0, "c": 0.0}
    assert "no canonically proven provider ownership" in result.evidence[0].reasons[0]


def test_strategy_requires_same_role_sample_before_calling_ownership_unusual() -> None:
    candidates = (_candidate("a"), _candidate("b"))
    result = evaluate_provider_redistribution_strategy(
        candidates,
        provider_ids_by_candidate={"a": ("major_courage",), "b": ()},
    )

    assert result.score_by_candidate == {"a": 0.0, "b": 0.0}
    assert "insufficient same-role candidate sample" in result.evidence[0].reasons[0]
