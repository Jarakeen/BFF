from __future__ import annotations

import pytest

from minmax.passive_eligibility import CLASS_SKILL_LINES
from services.extreme_actual_heal_coverage_audit_service import (
    ExtremeActualHealCoverageAuditService,
)
from services.extreme_healing_class_passive_coverage_inventory import (
    IMPLEMENTED,
    NOT_APPLICABLE,
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


def test_ten_reviewed_families_have_explicit_coverage_classification() -> None:
    rows = ExtremeHealingClassPassiveCoverageInventory().items()
    reviewed = [row for row in rows if row.review_status == REVIEWED]
    partial = [row for row in rows if row.review_status == PARTIAL]

    assert [(row.eso_class, row.skill_line) for row in reviewed] == [
        ("arcanist", "Curative Runeforms"),
        ("necromancer", "Living Death"),
        ("nightblade", "Siphoning"),
        ("sorcerer", "Dark Magic"),
        ("templar", "Aedric Spear"),
        ("templar", "Dawn's Wrath"),
        ("templar", "Restoring Light"),
        ("warden", "Animal Companions"),
        ("warden", "Green Balance"),
        ("warden", "Winter's Embrace"),
    ]
    relevant = [row for row in reviewed if row.healing_relevant is True]
    non_relevant = [row for row in reviewed if row.healing_relevant is False]
    assert len(relevant) == 9
    assert all(row.coverage_status == IMPLEMENTED for row in relevant)
    assert all(row.implemented_hook for row in relevant)
    assert [(row.eso_class, row.skill_line) for row in non_relevant] == [
        ("warden", "Winter's Embrace"),
    ]
    assert non_relevant[0].coverage_status == NOT_APPLICABLE
    assert not non_relevant[0].implemented_hook
    assert partial == []


def test_inventory_summary_counts_completed_warden_reviews() -> None:
    summary = ExtremeHealingClassPassiveCoverageInventory().summary()

    assert summary.total_families == 21
    assert summary.reviewed_families == 10
    assert summary.partially_reviewed_families == 0
    assert summary.unreviewed_families == 11
    assert summary.healing_relevant_families == 9
    assert summary.implemented == 9
    assert summary.explicitly_unsupported == 0
    assert summary.healing_relevant_unreviewed == 0
    assert summary.implemented_hooks == 9
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


def test_actual_heal_audit_reports_ten_reviewed_families_but_review_incomplete() -> None:
    audit = ExtremeActualHealCoverageAuditService()
    summary = audit.class_passive_summary()
    row = next(
        item
        for item in audit.items()
        if item.mechanic_id == "reviewed_class_passive_families"
    )

    assert summary.reviewed_families == 10
    assert summary.partially_reviewed_families == 0
    assert summary.unreviewed_families == 11
    assert summary.implemented == 9
    assert summary.explicitly_unsupported == 0
    assert summary.healing_relevant_unreviewed == 0
    assert row.status == "unresolved"
    assert row.evidence == "ExtremeHealingClassPassiveCoverageInventory"
    assert "reviewed 10/21" in row.detail
    assert "implemented 9" in row.detail
    assert "explicitly unsupported 0" in row.detail
    assert "families awaiting relevance review 11" in row.detail
    assert "reviewed_class_passive_families" in audit.summary().blocker_ids
