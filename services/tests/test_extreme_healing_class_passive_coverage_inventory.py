from __future__ import annotations

import pytest

from minmax.passive_eligibility import CLASS_SKILL_LINES
from services.extreme_actual_heal_coverage_audit_service import (
    ExtremeActualHealCoverageAuditService,
)
from services.extreme_healing_class_passive_coverage_inventory import (
    IMPLEMENTED,
    PARTIAL,
    REVIEWED,
    ExtremeHealingClassPassiveCoverageInventory,
)


def test_inventory_exactly_matches_canonical_class_skill_line_universe() -> None:
    rows = ExtremeHealingClassPassiveCoverageInventory().items()
    canonical = [
        (eso_class, skill_line)
        for eso_class, skill_lines in CLASS_SKILL_LINES.items()
        for skill_line in skill_lines
    ]

    assert len(rows) == 21
    assert [(row.eso_class, row.skill_line) for row in rows] == canonical
    assert len({row.family_id for row in rows}) == len(rows)


def test_four_reviewed_families_are_fully_implemented() -> None:
    rows = ExtremeHealingClassPassiveCoverageInventory().items()
    reviewed = [row for row in rows if row.review_status == REVIEWED]
    partial = [row for row in rows if row.review_status == PARTIAL]

    assert [(row.eso_class, row.skill_line) for row in reviewed] == [
        ("necromancer", "Living Death"),
        ("nightblade", "Siphoning"),
        ("templar", "Restoring Light"),
        ("warden", "Green Balance"),
    ]
    assert all(row.healing_relevant is True for row in reviewed)
    assert all(row.coverage_status == IMPLEMENTED for row in reviewed)
    assert all(row.implemented_hook for row in reviewed)
    assert partial == []


def test_inventory_summary_counts_four_completed_families() -> None:
    summary = ExtremeHealingClassPassiveCoverageInventory().summary()

    assert summary.total_families == 21
    assert summary.reviewed_families == 4
    assert summary.partially_reviewed_families == 0
    assert summary.unreviewed_families == 17
    assert summary.healing_relevant_families == 4
    assert summary.implemented == 4
    assert summary.explicitly_unsupported == 0
    assert summary.healing_relevant_unreviewed == 0
    assert summary.implemented_hooks == 4
    assert not summary.complete


def test_inventory_fails_closed_when_canonical_class_family_is_added_without_review_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        CLASS_SKILL_LINES,
        "test_class",
        ("Unreviewed Test Family",),
    )

    with pytest.raises(ValueError, match="must exactly match canonical class skill lines"):
        ExtremeHealingClassPassiveCoverageInventory().items()


def test_actual_heal_audit_reports_restoring_light_as_implemented_family() -> None:
    audit = ExtremeActualHealCoverageAuditService()
    summary = audit.class_passive_summary()
    row = next(
        item
        for item in audit.items()
        if item.mechanic_id == "reviewed_class_passive_families"
    )

    assert summary.reviewed_families == 4
    assert summary.partially_reviewed_families == 0
    assert summary.unreviewed_families == 17
    assert summary.implemented == 4
    assert summary.explicitly_unsupported == 0
    assert summary.healing_relevant_unreviewed == 0
    assert row.status == "unresolved"
    assert row.evidence == "ExtremeHealingClassPassiveCoverageInventory"
    assert "reviewed 4/21" in row.detail
    assert "implemented 4" in row.detail
    assert "explicitly unsupported 0" in row.detail
    assert "families awaiting relevance review 17" in row.detail
    assert "reviewed_class_passive_families" in audit.summary().blocker_ids
