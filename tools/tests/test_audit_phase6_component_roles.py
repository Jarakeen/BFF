from tools.audit_phase6_component_roles import ComponentRoleAuditRow, summarize


def test_summarize_counts_component_role_promotions():
    rows = (
        ComponentRoleAuditRow(1, 2, 10, "Trap", "additional_damage", ("additional_damage",), "x"),
        ComponentRoleAuditRow(2, 2, 20, "Barrier", "additional_heal", ("additional_heal",), "y"),
        ComponentRoleAuditRow(3, 2, 30, "Other", "additional_damage", (), "z"),
    )
    summary = summarize(rows)
    assert summary["candidates"] == 3
    assert summary["promoted"] == 2
    assert summary["unresolved"] == 1
    assert summary["roles"]["additional_damage"] == 1
    assert summary["roles"]["additional_heal"] == 1
