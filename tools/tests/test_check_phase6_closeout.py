from collections import Counter

from tools import check_phase6_closeout as gate


class _Row:
    def __init__(
        self,
        status,
        disposition="richer_component_semantics",
        *,
        skill_rank_id=1,
        coefficient_number=1,
    ):
        self.closeout_status = status
        self.disposition = disposition
        self.skill_rank_id = skill_rank_id
        self.coefficient_number = coefficient_number


class _FakeSourceIssueRepository:
    def __init__(self, _path, covered=()):
        self.covered = set(covered)

    def resolve(self, skill_rank_id, coefficient_number):
        return (object(),) if (skill_rank_id, coefficient_number) in self.covered else ()


def _summary(rows):
    statuses = Counter(row.closeout_status for row in rows)
    return {
        "rows": len(rows),
        "statuses": statuses,
        "needs_review": statuses["NEEDS_PHASE6_REVIEW"],
        "review_reasons": Counter(),
    }


def _patch_source_repo(monkeypatch, covered=()):
    monkeypatch.setattr(
        gate,
        "SkillComponentSourceAlignmentIssueRepository",
        lambda path: _FakeSourceIssueRepository(path, covered),
    )


def test_gate_passes_when_only_allowed_residuals_remain(monkeypatch):
    rows = (
        _Row("CLASSIFICATION_CLEANUP", "classification_field_gap"),
        _Row("PHASE7_BOUNDARY", "phase7_boundary_candidate"),
        _Row("OWNERSHIP_NEGATIVE"),
    )
    monkeypatch.setattr(gate, "load_phase6_closeout", lambda _path: rows)
    monkeypatch.setattr(gate, "summarize", _summary)
    _patch_source_repo(monkeypatch)

    passed, details = gate.evaluate_phase6_closeout("ignored.db")

    assert passed is True
    assert details["needs_review"] == 0
    assert details["parser_rows"] == 0
    assert details["source_blocked"] == 0
    assert details["unsupported_source_alignment"] == 0
    assert details["unresolved_source_blocked"] == 0
    assert details["unexpected"] == {}


def test_gate_fails_on_phase6_review(monkeypatch):
    rows = (_Row("NEEDS_PHASE6_REVIEW"),)
    monkeypatch.setattr(gate, "load_phase6_closeout", lambda _path: rows)
    monkeypatch.setattr(gate, "summarize", _summary)
    _patch_source_repo(monkeypatch)

    passed, details = gate.evaluate_phase6_closeout("ignored.db")

    assert passed is False
    assert details["needs_review"] == 1


def test_gate_fails_on_parser_coverage_even_if_status_is_misclassified(monkeypatch):
    rows = (_Row("CLASSIFICATION_CLEANUP", "parser_coverage"),)
    monkeypatch.setattr(gate, "load_phase6_closeout", lambda _path: rows)
    monkeypatch.setattr(gate, "summarize", _summary)
    _patch_source_repo(monkeypatch)

    passed, details = gate.evaluate_phase6_closeout("ignored.db")

    assert passed is False
    assert details["parser_rows"] == 1


def test_gate_fails_on_unexplained_source_evidence_block(monkeypatch):
    rows = (_Row("SOURCE_EVIDENCE_BLOCKED", "source_evidence"),)
    monkeypatch.setattr(gate, "load_phase6_closeout", lambda _path: rows)
    monkeypatch.setattr(gate, "summarize", _summary)
    _patch_source_repo(monkeypatch)

    passed, details = gate.evaluate_phase6_closeout("ignored.db")

    assert passed is False
    assert details["source_blocked"] == 1
    assert details["unsupported_source_alignment"] == 0
    assert details["unresolved_source_blocked"] == 1


def test_gate_passes_on_explicitly_classified_unsupported_source_alignment(monkeypatch):
    rows = (
        _Row(
            "SOURCE_EVIDENCE_BLOCKED",
            "source_evidence",
            skill_rank_id=4500,
            coefficient_number=3,
        ),
    )
    monkeypatch.setattr(gate, "load_phase6_closeout", lambda _path: rows)
    monkeypatch.setattr(gate, "summarize", _summary)
    _patch_source_repo(monkeypatch, {(4500, 3)})

    passed, details = gate.evaluate_phase6_closeout("ignored.db")

    assert passed is True
    assert details["source_blocked"] == 1
    assert details["unsupported_source_alignment"] == 1
    assert details["unresolved_source_blocked"] == 0
    assert details["unexpected"] == {}
