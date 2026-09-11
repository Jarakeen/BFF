from __future__ import annotations

from types import SimpleNamespace

import tools.audit_extreme_gear_search_completeness as tool


class _Repository:
    def __init__(self, path):
        self.path = path


class _TopologyService:
    def __init__(self, repository):
        self.repository = repository

    def build(self):
        return SimpleNamespace(
            sets=(SimpleNamespace(set_id=10, name="Known Set"),),
            unresolved=(),
        )


class _BreakpointService:
    def __init__(self, repository):
        self.repository = repository

    def build(self):
        return SimpleNamespace(unresolved=())


class _EligibilityService:
    def __init__(self, path):
        self.path = path

    def build(self):
        return SimpleNamespace(unresolved=())


class _RelevanceService:
    def __init__(self, repository):
        self.repository = repository

    def build(self, objective, breakpoints):
        return SimpleNamespace(objective_key=objective, unresolved=())


class _AuditService:
    proven = True

    @staticmethod
    def build(**kwargs):
        return SimpleNamespace(
            objective_key=kwargs["relevance"].objective_key,
            canonical_sets_reviewed=1,
            mechanically_relevant_breakpoints=1,
            relevance_breakpoints_reviewed=1,
            denominator_proven=_AuditService.proven,
            missing_from_breakpoints=(),
            missing_from_slot_eligibility=(),
            extra_breakpoint_sets=(),
            extra_slot_eligibility_sets=(),
            missing_relevance_breakpoints=(),
            extra_relevance_breakpoints=(),
            candidate_sets_without_slot_evidence=(),
            unresolved=() if _AuditService.proven else ("fixture blocker",),
        )


def _patch(monkeypatch):
    monkeypatch.setattr(tool, "GearSetRepository", _Repository)
    monkeypatch.setattr(tool, "ExtremeGearSetTopologyCatalogService", _TopologyService)
    monkeypatch.setattr(tool, "ExtremeGearSetBonusBreakpointService", _BreakpointService)
    monkeypatch.setattr(tool, "ExtremeNamedGearSetSlotEligibilityService", _EligibilityService)
    monkeypatch.setattr(tool, "ExtremeGearSetObjectiveRelevanceService", _RelevanceService)
    monkeypatch.setattr(tool, "ExtremeGearSearchCompletenessAuditService", _AuditService)


def test_tool_returns_zero_for_proven_denominator(monkeypatch, capsys):
    _patch(monkeypatch)
    _AuditService.proven = True
    monkeypatch.setattr(
        tool.sys,
        "argv",
        ["audit_extreme_gear_search_completeness.py", "--database", "fake.db", "--objective", "max_health"],
    )

    assert tool.main() == 0
    output = capsys.readouterr().out
    assert "EXTREME GEAR SEARCH COMPLETENESS AUDIT" in output
    assert "MAX_HEALTH" in output
    assert "Named-gear denominator proven: yes" in output


def test_tool_returns_two_when_denominator_is_open(monkeypatch, capsys):
    _patch(monkeypatch)
    _AuditService.proven = False
    monkeypatch.setattr(
        tool.sys,
        "argv",
        ["audit_extreme_gear_search_completeness.py", "--database", "fake.db", "--objective", "max_magicka"],
    )

    assert tool.main() == 2
    output = capsys.readouterr().out
    assert "Named-gear denominator proven: no" in output
    assert "fixture blocker" in output
