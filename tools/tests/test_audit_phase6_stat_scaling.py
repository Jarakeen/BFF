from tools.audit_phase6_stat_scaling import StatScalingAuditRow, summarize


def test_stat_scaling_audit_summary():
    rows = (
        StatScalingAuditRow(5578, 1, True, "health_recovery", "missing_health", 350.0),
        StatScalingAuditRow(5579, 1, True, "health_recovery", "missing_health", 700.0),
    )
    summary = summarize(rows)
    assert summary["candidates"] == 2
    assert summary["promoted"] == 2
    assert summary["unresolved"] == 0
    assert summary["stats"]["health_recovery"] == 2
    assert summary["drivers"]["missing_health"] == 2
