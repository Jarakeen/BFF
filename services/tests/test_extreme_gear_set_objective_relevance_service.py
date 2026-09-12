from __future__ import annotations

import pytest

from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
    ExtremeGearSetBonusBreakpoints,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_objective_service import (
    ExtremeGearSetObjectiveCandidate,
    ExtremeGearSetObjectiveService,
)


class _Set:
    def __init__(self, set_id: int, name: str):
        self.id = set_id
        self.name = name


class _Repository:
    def __init__(self):
        self.rows = {
            1: _Set(1, "Relevant Set"),
            2: _Set(2, "Irrelevant Set"),
            3: _Set(3, "Unresolved Set"),
            4: _Set(4, "Weaker Relevant Set"),
            5: _Set(5, "Magicka Only Set"),
            6: _Set(6, "Stamina Set"),
        }

    def get_set_by_id(self, set_id):
        return self.rows.get(int(set_id))


def _breakpoints(*rows, unresolved=()):
    return ExtremeGearSetBonusBreakpointCatalog(sets=tuple(rows), unresolved=tuple(unresolved))


def _row(set_id: int, name: str, *counts: int):
    return ExtremeGearSetBonusBreakpoints(
        set_id=set_id,
        name=name,
        max_equip_count=max(counts),
        bonus_counts=tuple(counts),
    )


def _candidate(set_id, name, piece_count, objective, delta, unresolved=()):
    return ExtremeGearSetObjectiveCandidate(
        set_id=set_id,
        set_name=name,
        category="Trial",
        equipped_piece_count=piece_count,
        objective_key=objective,
        reviewed_delta=delta,
        unresolved=tuple(unresolved),
    )


def test_positive_complete_breakpoint_is_relevant_and_zero_complete_is_safe_to_prune(monkeypatch):
    repository = _Repository()

    def fake_candidate(repo, set_name, objective_key, *, equipped_piece_count=None, resolver=None):
        if set_name == "Relevant Set":
            return _candidate(1, set_name, equipped_piece_count, objective_key, 1206.0)
        return _candidate(2, set_name, equipped_piece_count, objective_key, 0.0)

    monkeypatch.setattr(ExtremeGearSetObjectiveService, "candidate_for_set", fake_candidate)
    monkeypatch.setattr(ExtremeGearSetObjectiveService, "_target_stats", lambda key: {object()})

    catalog = ExtremeGearSetObjectiveRelevanceService(repository).build(
        "max_health",
        _breakpoints(
            _row(1, "Relevant Set", 2),
            _row(2, "Irrelevant Set", 2),
        ),
    )

    assert [row.status for row in catalog.evidence] == [
        ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT,
        ExtremeGearSetObjectiveRelevance.RELEVANT,
    ]
    irrelevant = next(row for row in catalog.evidence if row.set_id == 2)
    assert irrelevant.safe_to_prune is True
    assert catalog.candidate_set_ids == (1,)
    assert catalog.denominator_proven is True


def test_cross_resource_only_named_set_is_pruned_from_max_stamina_denominator(monkeypatch):
    repository = _Repository()

    def fake_candidate(repo, set_name, objective_key, *, equipped_piece_count=None, resolver=None):
        if set_name == "Stamina Set":
            return _candidate(6, set_name, equipped_piece_count, objective_key, 2000.0)
        return _candidate(5, set_name, equipped_piece_count, objective_key, 0.0)

    monkeypatch.setattr(ExtremeGearSetObjectiveService, "candidate_for_set", fake_candidate)
    monkeypatch.setattr(ExtremeGearSetObjectiveService, "_target_stats", lambda key: {object()})

    catalog = ExtremeGearSetObjectiveRelevanceService(repository).build(
        "max_stamina",
        _breakpoints(
            _row(5, "Magicka Only Set", 5),
            _row(6, "Stamina Set", 5),
        ),
    )

    magicka_only = next(row for row in catalog.evidence if row.set_id == 5)
    stamina = next(row for row in catalog.evidence if row.set_id == 6)
    assert magicka_only.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT
    assert magicka_only.safe_to_prune is True
    assert stamina.status is ExtremeGearSetObjectiveRelevance.RELEVANT
    assert catalog.candidate_set_ids == (6,)
    assert catalog.denominator_proven is True


def test_unresolved_relevant_bonus_is_never_pruned(monkeypatch):
    repository = _Repository()

    monkeypatch.setattr(ExtremeGearSetObjectiveService, "_target_stats", lambda key: {object()})
    monkeypatch.setattr(
        ExtremeGearSetObjectiveService,
        "candidate_for_set",
        lambda repo, set_name, objective_key, *, equipped_piece_count=None, resolver=None: _candidate(
            3,
            set_name,
            equipped_piece_count,
            objective_key,
            0.0,
            ("Unresolved Set (5): active set bonus is not yet mechanic-mapped",),
        ),
    )

    catalog = ExtremeGearSetObjectiveRelevanceService(repository).build(
        "spell_damage",
        _breakpoints(_row(3, "Unresolved Set", 5)),
    )

    assert catalog.evidence[0].status is ExtremeGearSetObjectiveRelevance.UNRESOLVED
    assert catalog.evidence[0].safe_to_prune is False
    assert catalog.candidate_set_ids == (3,)
    assert catalog.denominator_proven is False
    assert "not yet mechanic-mapped" in catalog.unresolved[0]


def test_breakpoint_catalog_unresolved_evidence_blocks_denominator_proof(monkeypatch):
    repository = _Repository()
    monkeypatch.setattr(ExtremeGearSetObjectiveService, "_target_stats", lambda key: {object()})
    monkeypatch.setattr(
        ExtremeGearSetObjectiveService,
        "candidate_for_set",
        lambda repo, set_name, objective_key, *, equipped_piece_count=None, resolver=None: _candidate(
            1, set_name, equipped_piece_count, objective_key, 100.0
        ),
    )

    catalog = ExtremeGearSetObjectiveRelevanceService(repository).build(
        "max_health",
        _breakpoints(
            _row(1, "Relevant Set", 2),
            unresolved=("Mystery Set has invalid bonus threshold",),
        ),
    )

    assert catalog.relevant
    assert catalog.denominator_proven is False
    assert catalog.unresolved == ("Mystery Set has invalid bonus threshold",)


def test_two_positive_sets_are_both_retained_without_unsafe_cross_set_dominance(monkeypatch):
    repository = _Repository()

    def fake_candidate(repo, set_name, objective_key, *, equipped_piece_count=None, resolver=None):
        delta = 500.0 if set_name == "Relevant Set" else 200.0
        set_id = 1 if set_name == "Relevant Set" else 4
        return _candidate(set_id, set_name, equipped_piece_count, objective_key, delta)

    monkeypatch.setattr(ExtremeGearSetObjectiveService, "_target_stats", lambda key: {object()})
    monkeypatch.setattr(ExtremeGearSetObjectiveService, "candidate_for_set", fake_candidate)

    catalog = ExtremeGearSetObjectiveRelevanceService(repository).build(
        "spell_damage",
        _breakpoints(
            _row(1, "Relevant Set", 5),
            _row(4, "Weaker Relevant Set", 5),
        ),
    )

    assert catalog.candidate_set_ids == (1, 4)
    assert len(catalog.relevant) == 2
    assert not catalog.proven_irrelevant


def test_missing_canonical_set_for_breakpoint_fails_closed(monkeypatch):
    repository = _Repository()
    monkeypatch.setattr(ExtremeGearSetObjectiveService, "_target_stats", lambda key: {object()})

    catalog = ExtremeGearSetObjectiveRelevanceService(repository).build(
        "max_health",
        _breakpoints(_row(999, "Missing Set", 2)),
    )

    assert catalog.evidence == ()
    assert catalog.denominator_proven is False
    assert catalog.candidate_set_ids == ()
    assert "missing from canonical repository" in catalog.unresolved[0]


def test_unreviewed_objective_fails_closed_before_classification():
    with pytest.raises(KeyError, match="unreviewed Extreme gear-set objective"):
        ExtremeGearSetObjectiveRelevanceService(_Repository()).build(
            "actual_heal",
            _breakpoints(_row(1, "Relevant Set", 2)),
        )
