from __future__ import annotations

import pytest

from services.canonical_knowledge_gap import CanonicalKnowledgeDomain
from services.canonical_mechanics_coverage_audit import (
    CanonicalMechanicsCoverageAuditService,
    CanonicalMechanicsCoverageEvidence,
    CanonicalMechanicsCoverageStatus,
)
from services.canonical_mechanics_coverage_inventory import (
    shared_canonical_mechanics_inventory,
)


def _row(
    *,
    key: str,
    status: CanonicalMechanicsCoverageStatus,
    missing: str | None = None,
    consumers=("rotation_maker", "optimizer"),
) -> CanonicalMechanicsCoverageEvidence:
    return CanonicalMechanicsCoverageEvidence(
        domain=CanonicalKnowledgeDomain.SKILL_MECHANIC,
        key=key,
        status=status,
        capability=f"capability for {key}",
        evidence_source="verified test source",
        consumers=consumers,
        missing_evidence=missing,
    )


def test_partial_and_missing_rows_become_advisory_and_blocking_gaps() -> None:
    rows = (
        _row(key="ready", status=CanonicalMechanicsCoverageStatus.CALCULATION_READY),
        _row(
            key="partial",
            status=CanonicalMechanicsCoverageStatus.PARTIAL,
            missing="verify remaining runtime behavior",
        ),
        _row(
            key="critical",
            status=CanonicalMechanicsCoverageStatus.MISSING_CRITICAL,
            missing="bring back exact decision-critical evidence",
            consumers=("comp_maker", "rotation_maker", "optimizer"),
        ),
        _row(key="niche", status=CanonicalMechanicsCoverageStatus.NICHE),
    )

    report = CanonicalMechanicsCoverageAuditService().audit(rows)

    assert report.rows == rows
    assert [gap.key for gap in report.knowledge_gaps] == ["partial", "critical"]
    assert report.knowledge_gaps[0].needed_evidence == "verify remaining runtime behavior"
    assert report.knowledge_gaps[0].blocking is False
    assert report.knowledge_gaps[1].blocking is True
    assert report.knowledge_gaps[1].consumers == (
        "comp_maker",
        "rotation_maker",
        "optimizer",
    )
    assert [gap.key for gap in report.advisory_gaps] == ["partial"]
    assert [gap.key for gap in report.decision_critical_gaps] == ["critical"]


def test_report_filters_rows_and_gaps_by_consumer_and_status() -> None:
    report = CanonicalMechanicsCoverageAuditService().audit(
        (
            _row(
                key="shared",
                status=CanonicalMechanicsCoverageStatus.PARTIAL,
                missing="more evidence",
                consumers=("comp_maker", "optimizer"),
            ),
            _row(
                key="rotation-only",
                status=CanonicalMechanicsCoverageStatus.PARTIAL,
                missing="timing evidence",
                consumers=("rotation_maker",),
            ),
        )
    )

    assert [row.key for row in report.rows_for("OPTIMIZER")] == ["shared"]
    assert [gap.key for gap in report.gaps_for("rotation_maker")] == ["rotation-only"]
    assert [row.key for row in report.by_status(CanonicalMechanicsCoverageStatus.PARTIAL)] == [
        "shared",
        "rotation-only",
    ]


def test_partial_or_critical_coverage_requires_explicit_missing_evidence() -> None:
    with pytest.raises(ValueError, match="requires missing_evidence"):
        _row(key="bad-partial", status=CanonicalMechanicsCoverageStatus.PARTIAL)

    with pytest.raises(ValueError, match="requires missing_evidence"):
        _row(
            key="bad-critical",
            status=CanonicalMechanicsCoverageStatus.MISSING_CRITICAL,
        )


def test_duplicate_coverage_keys_fail_closed() -> None:
    row = _row(key="same", status=CanonicalMechanicsCoverageStatus.CALCULATION_READY)
    with pytest.raises(ValueError, match="duplicate canonical mechanics coverage key"):
        CanonicalMechanicsCoverageAuditService().audit((row, row))


def test_seed_inventory_spans_shared_decision_domains_and_emits_research_queue() -> None:
    rows = shared_canonical_mechanics_inventory()
    report = CanonicalMechanicsCoverageAuditService().audit(rows)

    assert len(rows) >= 10
    assert any(row.status is CanonicalMechanicsCoverageStatus.CALCULATION_READY for row in rows)
    assert any(row.status is CanonicalMechanicsCoverageStatus.PARTIAL for row in rows)
    assert any(row.status is CanonicalMechanicsCoverageStatus.NICHE for row in rows)

    keys = {row.key for row in rows}
    assert "effect_duration:build_modifiers" in keys
    assert "heavy_attack:restoration" in keys
    assert "assignment:rotation_fulfillment_catalog" in keys
    assert "passives:runtime_semantics" in keys
    assert "gear:conditional_topology" in keys
    assert "skills:runtime_topology" in keys
    assert "consumables:runtime_resource_and_buff_policy" in keys
    assert "weapons:bash_interrupt_poison_topology" in keys
    assert "encounter:target_range_movement_topology" in keys

    assert report.gaps_for("comp_maker")
    assert report.gaps_for("rotation_maker")
    assert report.gaps_for("optimizer")
    assert report.advisory_gaps
