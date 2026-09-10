from __future__ import annotations

import pytest

from minmax.passive_eligibility import CLASS_SKILL_LINES
from services.extreme_actual_heal_coverage_audit_service import (
    ExtremeActualHealCoverageAuditService,
)
from services.extreme_healing_class_passive_coverage_inventory import (
    EXPLICITLY_UNSUPPORTED,
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


def test_six_reviewed_families_include_explicit_dark_magic_blocker() -> None:
    rows = ExtremeHealingClassPassiveCoverageInventory().items()
    reviewed = [row for row in rows if row.review_status == REVIEWED]
    partial = [row for row in rows if row.review_status == PARTIAL]

    assert [(row.eso_class, row.skill_line) for row in reviewed] == [
        ("arcanist", "Curative Runeforms"),
        ("necromancer", "Living Death"),
        ("nightblade", "Siphoning"),
        ("sorcerer", "Dark Magic"),
        ("templar", "Restoring Light"),
        ("warden", "Green Balance"),
    ]
    assert all(row.healing_relevant is True for row in reviewed)
    assert {
        (row.eso_class, row.skill_line): row.coverage_status
        for row in reviewed
    } == {
        ("arcanist", "Curative Runeforms"): IMPLEMENTED,
        ("necromancer", "Living Death"): IMPLEMENTED,
        ("nightblade", "Siphoning"): IMPLEMENTED,
        ("sorcerer", "Dark Magic"): EXPLICITLY_UNSUPPORTED,
        ("templar", "Restoring Light"): IMPLEMENTED,
        ("warden", "Green Balance"): IMPLEMENTED,
    }
    assert not next(
        row for row in reviewed if row.family_id == "sorcerer:Dark Magic"
    ).implemented_hook
    assert partial == []


def test_inventory_summary_counts_dark_magic_review_and_blocker() -> None:
    summary = ExtremeHealingClassPassiveCoverageInventory().summary()

    assert summary.total_families == 21
    assert summary.reviewed_families == 6
    assert summary.partially_reviewed_families == 0
    assert summary.unreviewed_families == 15
    assert summary.healing_relevant_families == 6
    assert summary.implemented == 5
    assert summary.explicitly_unsupported == 1
    assert summary.healing_relevant_unreviewed == 0
    assert summary.implemented_hooks == 5
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


def test_actual_heal_audit_reports_dark_magic_as_explicitly_unsupported() -> None:
    audit = ExtremeActualHealCoverageAuditService()
    summary = audit.class_passive_summary()
    row = next(
        item
        for item in audit.items()
        if item.mechanic_id == "reviewed_class_passive_families"
    )

    assert summary.reviewed_families == 6
    assert summary.partially_reviewed_families == 0
    assert summary.unreviewed_families == 15
    assert summary.implemented == 5
    assert summary.explicitly_unsupported == 1
    assert summary.healing_relevant_unreviewed == 0
    assert row.status == "unresolved"
    assert row.evidence == "ExtremeHealingClassPassiveCoverageInventory"
    assert "reviewed 6/21" in row.detail
    assert "implemented 5" in row.detail
    assert "explicitly unsupported 1" in row.detail
    assert "families awaiting relevance review 15" in row.detail
    assert "reviewed_class_passive_families" in audit.summary().blocker_ids
