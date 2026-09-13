from __future__ import annotations

from tools.audit_phase13_dd_periodic_review_backlog import audit


def test_periodic_review_backlog_audit_reports_partial_and_complete(capsys) -> None:
    assert audit() == 0
    text = capsys.readouterr().out

    assert "DD PERIODIC RUNTIME REVIEW BACKLOG" in text
    assert "unnerving_boneyard" in text
    assert "first_tick_offset_seconds" in text
    assert "magnitude_policy" in text
    assert "stampede" in text
    assert "COMPLETE" in text
    assert "PARTIAL" in text
    assert "this audit does not infer or promote missing mechanics" in text
