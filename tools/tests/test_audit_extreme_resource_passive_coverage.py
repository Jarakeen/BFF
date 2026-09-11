from __future__ import annotations

from types import SimpleNamespace

import tools.audit_extreme_resource_passive_coverage as tool


class _Service:
    def __init__(self, database):
        self.database = database

    def build(self, objective):
        return SimpleNamespace(
            passives_reviewed=5,
            denominator_proven=True,
            projection_complete=False,
            static_relevant=(f"[class] Test Line :: {objective} Passive",),
            accounted_elsewhere=("[racial] Imperial Skills :: Tough",),
            static_irrelevant=("[utility] Utility :: Irrelevant",),
            context_required=("[guild] Mages Guild :: Magicka Controller",),
            unresolved=("[world] Vampire :: Mystery Passive",),
        )


def test_cli_reports_all_three_resource_objectives(monkeypatch, capsys):
    monkeypatch.setattr(tool, "ExtremeResourcePassiveCoverageAuditService", _Service)
    monkeypatch.setattr(tool.sys, "argv", ["audit_extreme_resource_passive_coverage.py", "--database", "fake.db"])

    assert tool.main() == 0
    output = capsys.readouterr().out
    assert "MAX_HEALTH" in output
    assert "MAX_MAGICKA" in output
    assert "MAX_STAMINA" in output
    assert "Passives reviewed: 5" in output
    assert "Inventory denominator proven: yes" in output
    assert "Static projection complete: no" in output
    assert "Accounted elsewhere: 1" in output
    assert "Imperial Skills :: Tough" in output
    assert "Magicka Controller" in output
    assert "Mystery Passive" in output


def test_cli_can_limit_objective(monkeypatch, capsys):
    monkeypatch.setattr(tool, "ExtremeResourcePassiveCoverageAuditService", _Service)
    monkeypatch.setattr(
        tool.sys,
        "argv",
        [
            "audit_extreme_resource_passive_coverage.py",
            "--database",
            "fake.db",
            "--objective",
            "max_health",
        ],
    )

    assert tool.main() == 0
    output = capsys.readouterr().out
    assert "MAX_HEALTH" in output
    assert "MAX_MAGICKA" not in output
    assert "MAX_STAMINA" not in output
