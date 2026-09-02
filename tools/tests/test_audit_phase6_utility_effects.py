from tools.audit_phase6_utility_effects import UtilityAuditRow, summarize


def test_summarize_counts_promoted_context_neighbor_owned_and_unresolved_utility_effects():
    rows = (
        UtilityAuditRow(1, 1, 10, "A", ("stun",), "stuns"),
        UtilityAuditRow(2, 1, 20, "B", ("movement_speed_reduction",), "reduces Movement Speed"),
        UtilityAuditRow(
            3,
            1,
            30,
            "C",
            (),
            "if the stun lasts",
            context_only=True,
        ),
        UtilityAuditRow(
            4,
            1,
            40,
            "D",
            (),
            "neighbor utility mention",
            neighboring_owner=2,
            neighboring_types=("interrupt_immunity",),
        ),
        UtilityAuditRow(5, 1, 50, "E", (), "unresolved utility mention"),
    )
    summary = summarize(rows)
    assert summary["candidates"] == 5
    assert summary["promoted"] == 2
    assert summary["context_only"] == 1
    assert summary["neighbor_owned"] == 1
    assert summary["unresolved"] == 1
    assert summary["types"]["stun"] == 1
    assert summary["types"]["movement_speed_reduction"] == 1
    assert summary["neighbor_types"]["interrupt_immunity"] == 1
