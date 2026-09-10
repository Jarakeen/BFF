from __future__ import annotations

import pytest

from minmax.passive_eligibility import CLASS_SKILL_LINES
from services.extreme_actual_heal_coverage_audit_service import (
    ExtremeActualHealCoverageAuditService,
)
from services.extreme_healing_class_passive_coverage_inventory import (
    PARTIAL,
    UNREVIEWED,
    ExtremeHealingClassPassiveCoverageInventory,
)


def test_inventory_exactly_matches_canonical_class_skill_line_universe() -> None:
    inventory = ExtremeHealingClassPassiveCoverageInventory()
    rows = inventory.items()
    canonical = {
        (eso_class, skill_line)
        for eso_class, skill_lines in CLASS_SKILL_LINES.items()
        for skill_line in skill_lines
    }

    assert len(rows) == 21
    assert {(row.eso_class, row.skill_line) for row in rows} == canonical
    assert len({row.family_id for row in rows}) == len(rows)


def test_inventory_keeps_existing_healing_hooks_partial_until_family_review_is_complete() -> None:
    rows = ExtremeHealingClassPassiveCoverageInventory().items()
    partial = {
        (row.eso_class, row.skill_line): row
        for row in rows
        if row.review_status == PARTIAL
    }

    assert set(partial) == {
        ("necromancer", "Living Death"),
        ("nightblade", "Siphoning"),
        ("warden", "Green Balance"),
    }
    assert all(row.healing_relevant is True for row in partial.values())
    assert all(row.coverage_status == UNREVIEWED for row in partial.values())
    assert all(row.implemented_hook for row in partial.values())
    assert all(
        row.review_status == UNREVIEWED
        for row in rows
        if (row.eso_class, row.skill_line) not in partial
    )


def test_inventory_summary_exposes_countable_review_denominator() -> None:
    summary = ExtremeHealingClassPassiveCoverageInventory().summary()

    assert summary.total_families == 21
    assert summary.reviewed_families == 0
    assert summary.partially_reviewed_families == 3
    assert summary.unreviewed_families == 18
    assert summary.healing_relevant_families == 3
    assert summary.implemented == 0
    assert summary.explicitly_unsupported == 0
    assert summary.healing_relevant_unreviewed == 3
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


def test_actual_heal_audit_derives_class_passive_blocker_from_inventory() -> None:
    audit = ExtremeActualHealCoverageAuditService()
    summary = audit.class_passive_summary()
    row = next(
        item
        for item in audit.items()
        if item.mechanic_id == "reviewed_class_passive_families"
    )

    assert summary.partially_reviewed_families == 3
    assert summary.unreviewed_families == 18
    assert summary.healing_relevant_unreviewed == 3
    assert row.status == "unresolved"
    assert row.evidence == "ExtremeHealingClassPassiveCoverageInventory"
    assert "reviewed 0/21" in row.detail
    assert "healing-relevant unreviewed 3" in row.detail
    assert "families awaiting relevance review 18" in row.detail
    assert "reviewed_class_passive_families" in audit.summary().blocker_ids
