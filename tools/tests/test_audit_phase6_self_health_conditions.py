from tools.audit_phase6_self_health_conditions import SelfHealthConditionAuditRow, summarize


def test_summarize_counts_self_health_condition_promotions():
    rows = (
        SelfHealthConditionAuditRow(1, 1, 10, "Soul Shatter", True, 0.20, "your Health drops below 20%"),
        SelfHealthConditionAuditRow(2, 1, 20, "Other", False, None, "your Health drops below 30%"),
    )

    summary = summarize(rows)

    assert summary["candidates"] == 2
    assert summary["promoted"] == 1
    assert summary["unresolved"] == 1
    assert summary["thresholds"][0.20] == 1
