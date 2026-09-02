from collections import Counter
from types import SimpleNamespace

from tools import check_phase6_closeout as gate


class _Row:
    def __init__(self, status, disposition="richer_component_semantics"):
        self.closeout_status = status
        self.disposition = disposition


def _summary(rows):
    statuses = Counter(row.closeout_status for row in rows)
    return {
        "rows": len(rows),
        "statuses": statuses,
        "needs_review": statuses["NEEDS_PHASE6_REVIEW"],
        "review_reasons": Counter(),
    }


def test_gate_passes_when_only_allowed_residuals_remain(monkeypatch):
    rows = (
        _Row("CLASSIFICATION_CLEANUP", "classification_field_gap"),
        _Row("PHASE7_BOUNDARY", "phase7_boundary_candidate"),
        _Row("OWNERSHIP_NEGATIVE"),
    )
    monkeypatch.setattr(gate, "load_phase6_closeout", lambda _path: rows)
    monkeypatch.setattr(gate, "summarize", _summary)

    passed, details = gate.evaluate_phase6_closeout("ignored.db")

    assert passed is True
    assert details["needs_review"] == 0
    assert details["parser_rows"] == 0
    assert details["source_blocked"] == 0
    assert details["unexpected"] == {}


def test_gate_fails_on_phase6_review(monkeypatch):
    rows = (_Row("NEEDS_PHASE6_REVIEW"),)
    monkeypatch.setattr(gate, "load_phase6_closeout", lambda _path: rows)
    monkeypatch.setattr(gate, "summarize", _summary)

    passed, details = gate.evaluate_phase6_closeout("ignored.db")

    assert passed is False
    assert details["needs_review"] == 1


def test_gate_fails_on_parser_coverage_even_if_status_is_misclassified(monkeypatch):
    rows = (_Row("CLASSIFICATION_CLEANUP", "parser_coverage"),)
    monkeypatch.setattr(gate, "load_phase6_closeout", lambda _path: rows)
    monkeypatch.setattr(gate, "summarize", _summary)

    passed, details = gate.evaluate_phase6_closeout("ignored.db")

    assert passed is False
    assert details["parser_rows"] == 1


def test_gate_fails_on_source_evidence_block(monkeypatch):
    rows = (_Row("SOURCE_EVIDENCE_BLOCKED", "source_evidence"),)
    monkeypatch.setattr(gate, "load_phase6_closeout", lambda _path: rows)
    monkeypatch.setattr(gate, "summarize", _summary)

    passed, details = gate.evaluate_phase6_closeout("ignored.db")

    assert passed is False
    assert details["source_blocked"] == 1
