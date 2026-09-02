from tools.audit_phase6_damage_scaling import DamageScalingAuditRow, summarize


def test_summarize_counts_promoted_damage_scaling():
    rows = (
        DamageScalingAuditRow(1, 2, 10, "A", ("accumulated_damage",), ("accumulated_damage",), "stored"),
        DamageScalingAuditRow(2, 1, 20, "B", ("per_tick_increment",), ("per_tick_increment",), "tick"),
        DamageScalingAuditRow(3, 1, 30, "C", ("per_tick_increment",), (), "unresolved"),
    )
    summary = summarize(rows)
    assert summary["candidates"] == 3
    assert summary["promoted"] == 2
    assert summary["unresolved"] == 1
    assert summary["types"]["accumulated_damage"] == 1
    assert summary["types"]["per_tick_increment"] == 1
