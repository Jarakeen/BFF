from __future__ import annotations

from tools.audit_phase13_dd_periodic_review_backlog import audit


def test_periodic_review_backlog_audit_reports_partial_parked_and_complete(capsys) -> None:
    assert audit() == 0
    text = capsys.readouterr().out

    assert "DD PERIODIC RUNTIME REVIEW BACKLOG" in text
    assert "unnerving_boneyard coeff=1: PARKED" in text
    assert "scalding_rune coeff=2: PARKED" in text
    assert "detonating_siphon coeff=1: PARKED" in text
    assert "skeletal_archer coeff=1: PARKED" in text
    assert "meteor coeff=2: PARKED" in text
    assert "flawless_dawnbreaker coeff=2: PARTIAL" in text
    assert "stampede coeff=2: COMPLETE" in text
    assert "Active partial reviews: 1" in text
    assert "Parked reviews: 5" in text
    assert "current corpus exposes no explicit pet-to-owner linkage for candidate 122774" in text
    assert "current evidence source has been exhausted or is non-discriminating" in text
