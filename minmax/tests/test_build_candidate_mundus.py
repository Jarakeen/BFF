from __future__ import annotations

from minmax.build_candidate_mundus import enumerate_mundus_candidates
from models.build_model import PlayerBuild


class _MundusRepository:
    def list_names(self) -> list[str]:
        return ["The Ritual", "The Shadow", "The Thief"]


def test_enumerate_mundus_candidates_changes_exactly_one_field() -> None:
    baseline = PlayerBuild(
        Name="Magrat",
        BuildName="DF Healer",
        Mundus="The Ritual",
        Food="Orzorga's Red Frothgar",
        AttributeMagicka=64,
    )

    candidates = enumerate_mundus_candidates(
        baseline_build=baseline,
        character_id="magrat",
        baseline_build_id="df-healer",
        mundus_repository=_MundusRepository(),
    )

    assert [candidate.candidate_build.Mundus for candidate in candidates] == [
        "The Shadow",
        "The Thief",
    ]
    assert [candidate.candidate_id for candidate in candidates] == [
        "df-healer:mundus:the-shadow",
        "df-healer:mundus:the-thief",
    ]
    assert all(len(candidate.changes) == 1 for candidate in candidates)
    assert all(candidate.changes[0].path == "Mundus" for candidate in candidates)
    assert all(candidate.changes[0].before == "The Ritual" for candidate in candidates)
    assert [candidate.changes[0].after for candidate in candidates] == [
        "The Shadow",
        "The Thief",
    ]
    assert all(candidate.candidate_build.Food == baseline.Food for candidate in candidates)
    assert all(candidate.candidate_build.AttributeMagicka == 64 for candidate in candidates)


def test_enumerate_mundus_candidates_never_mutates_baseline() -> None:
    baseline = PlayerBuild(Mundus="The Ritual")

    candidates = enumerate_mundus_candidates(
        baseline_build=baseline,
        character_id="magrat",
        baseline_build_id="df-healer",
        mundus_repository=_MundusRepository(),
    )
    first = candidates[0].candidate_build
    first.Mundus = "The Atronach"

    assert baseline.Mundus == "The Ritual"
    assert candidates[0].candidate_build.Mundus == "The Shadow"


def test_enumerate_mundus_candidates_allows_blank_baseline_without_guessing() -> None:
    baseline = PlayerBuild(Mundus="")

    candidates = enumerate_mundus_candidates(
        baseline_build=baseline,
        character_id="magrat",
        baseline_build_id="df-healer",
        mundus_repository=_MundusRepository(),
    )

    assert len(candidates) == 3
    assert all(candidate.changes[0].before == "" for candidate in candidates)
