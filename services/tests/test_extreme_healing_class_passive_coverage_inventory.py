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
    UNREVIEWED,
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


def test_green_balance_is_first_completed_family_review() -> None:
    rows = ExtremeHealingClassPassiveCoverageInventory().items()
    reviewed = [row for row in rows if row.review_status == REVIEWED]
    partial = {
        (row.eso_class, row.skill_line)
        for row in rows
        if row.review_status == PARTIAL
    }

    assert [(row.eso_class, row.skill_line) for row in reviewed] == [
        ("warden", "Green Balance")
    ]
    assert reviewed[0].healing_relevant is True
    assert reviewed[0].coverage_status == IMPLEMENTED
    assert reviewed[0].implemented_hook
    assert partial == {
        ("necromancer", "Living Death"),
        ("nightblade", "Siphoning"),
    }


def test_inventory_summary_counts_completed_green_balance_family() -> None:
    summary = ExtremeHealingClassPassiveCoverageInventory().summary()

    assert summary.total_families == 21
    assert summary.reviewed_families == 1
    assert summary.partially_reviewed_families == 2
    assert summary.unreviewed_families == 18
    assert summary.healing_relevant_families == 3
    assert summary.implemented == 1
    assert summary.explicitly_unsupported == 0
    assert summary.healing_relevant_unreviewed == 2
    assert summary.implemented_hooks == 3
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


def test_actual_heal_audit_derives_remaining_class_passive_blocker_from_inventory() -> None:
    audit = ExtremeActualHealCoverageAuditService()
    summary = audit.class_passive_summary()
    row = next(
        item
        for item in audit.items()
        if item.mechanic_id == "reviewed_class_passive_families"
    )

    assert summary.reviewed_families == 1
    assert summary.partially_reviewed_families == 2
    assert summary.unreviewed_families == 18
    assert summary.healing_relevant_unreviewed == 2
    assert row.status == "unresolved"
    assert row.evidence == "ExtremeHealingClassPassiveCoverageInventory"
    assert "reviewed 1/21" in row.detail
    assert "healing-relevant unreviewed 2" in row.detail
    assert "families awaiting relevance review 18" in row.detail
    assert "reviewed_class_passive_families" in audit.summary().blocker_ids
