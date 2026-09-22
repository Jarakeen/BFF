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


def test_partial_missing_and_niche_rows_become_advisory_or_blocking_gaps() -> None:
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
    assert [gap.key for gap in report.knowledge_gaps] == ["partial", "critical", "niche"]
    assert report.knowledge_gaps[0].needed_evidence == "verify remaining runtime behavior"
    assert report.knowledge_gaps[0].blocking is False
    assert report.knowledge_gaps[1].blocking is True
    assert report.knowledge_gaps[1].consumers == (
        "comp_maker",
        "rotation_maker",
        "optimizer",
    )
    assert report.knowledge_gaps[2].blocking is False
    assert "selected build, encounter, or objective" in report.knowledge_gaps[2].needed_evidence
    assert [gap.key for gap in report.advisory_gaps] == ["partial", "niche"]
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


def test_declared_dependencies_ignore_unrelated_critical_coverage() -> None:
    report = CanonicalMechanicsCoverageAuditService().audit(
        (
            _row(key="ready", status=CanonicalMechanicsCoverageStatus.CALCULATION_READY),
            _row(
                key="selected-partial",
                status=CanonicalMechanicsCoverageStatus.PARTIAL,
                missing="verify selected runtime behavior",
            ),
            _row(
                key="unrelated-critical",
                status=CanonicalMechanicsCoverageStatus.MISSING_CRITICAL,
                missing="critical evidence for a different mechanic",
            ),
        )
    )

    gaps = report.dependency_gaps_for(
        "rotation_maker",
        ("ready", "selected-partial", "selected-partial"),
    )

    assert [gap.key for gap in gaps] == ["selected-partial"]
    assert gaps[0].blocking is False


def test_declared_dependency_without_usable_coverage_fails_closed() -> None:
    report = CanonicalMechanicsCoverageAuditService().audit(
        (
            _row(
                key="optimizer-only",
                status=CanonicalMechanicsCoverageStatus.CALCULATION_READY,
                consumers=("optimizer",),
            ),
        )
    )

    gaps = report.dependency_gaps_for(
        "rotation_maker",
        ("missing-row", "optimizer-only"),
    )

    assert [gap.key for gap in gaps] == ["missing-row", "optimizer-only"]
    assert all(gap.blocking for gap in gaps)
    assert "no canonical coverage evidence" in gaps[0].summary
    assert "not covered for this consumer" in gaps[1].summary


def test_declared_dependency_rejects_blank_keys() -> None:
    report = CanonicalMechanicsCoverageAuditService().audit(())

    with pytest.raises(ValueError, match="dependency key must be non-empty"):
        report.dependency_gaps_for("rotation_maker", (" ",))

    with pytest.raises(ValueError, match="consumer must be non-empty"):
        report.dependency_gaps_for(" ", ())


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
    assert "armor:weight_passive_semantics" in keys
    assert "gear:conditional_topology" in keys
    assert "skills:runtime_topology" in keys
    assert "consumables:runtime_resource_and_buff_policy" in keys
    assert "weapon_enchantments:runtime_cadence" in keys
    assert "weapons:bash_interrupt_poison_topology" in keys
    assert "encounter:target_range_movement_topology" in keys

    passive_row = next(row for row in rows if row.key == "passives:runtime_semantics")
    assert passive_row.status is CanonicalMechanicsCoverageStatus.PARTIAL
    assert "context_factory.py" in passive_row.evidence_source
    assert "Warden" in passive_row.capability
    assert "Alliance Support" in passive_row.capability
    assert "racial_passive_stat_repository.py" in passive_row.evidence_source
    assert "phase5_context_factory.py" in passive_row.evidence_source
    assert "now reaches rotation static contexts" in passive_row.missing_evidence
    assert "extreme_passive_projection_service.py" in passive_row.evidence_source
    assert "fails conditional/runtime clauses closed" in passive_row.missing_evidence

    potion_row = next(
        row for row in rows if row.key == "consumables:runtime_resource_and_buff_policy"
    )
    assert potion_row.status is CanonicalMechanicsCoverageStatus.PARTIAL
    assert "rotation_plan_potion_combat_state_service.py" in potion_row.evidence_source
    assert "scheduled POTION actions" in potion_row.capability
    assert "already resolved scheduled buff windows" in potion_row.missing_evidence

    armor_row = next(row for row in rows if row.key == "armor:weight_passive_semantics")
    assert armor_row.status is CanonicalMechanicsCoverageStatus.PARTIAL
    assert "armor_passive_input_resolver.py" in armor_row.evidence_source
    assert "undaunted_passive_input_resolver.py" in armor_row.evidence_source
    assert "rotation_static_build_context_service.py" in armor_row.evidence_source
    assert "already reuses BuildCalculationContextFactory" in armor_row.capability

    armor_gaps = report.dependency_gaps_for(
        "rotation_maker",
        ("armor:weight_passive_semantics",),
    )
    assert len(armor_gaps) == 1
    assert armor_gaps[0].blocking is False

    assert report.gaps_for("comp_maker")
    assert report.gaps_for("rotation_maker")
    assert report.gaps_for("optimizer")
    assert report.advisory_gaps
    assert any(gap.key == "niche:stealth_thief_bash_objectives" for gap in report.advisory_gaps)


def test_weapon_enchantment_runtime_cadence_is_decision_critical_until_timing_is_proven() -> None:
    rows = shared_canonical_mechanics_inventory()
    report = CanonicalMechanicsCoverageAuditService().audit(rows)

    row = next(
        item for item in rows
        if item.key == "weapon_enchantments:runtime_cadence"
    )
    assert row.status is CanonicalMechanicsCoverageStatus.MISSING_CRITICAL
    assert "weapon_enchantment_effect_service.py" in row.evidence_source
    assert "combat_cooldown_rules.py" in row.evidence_source
    assert "activation trigger semantics" in row.missing_evidence
    assert "base proc cooldown" in row.missing_evidence

    rotation_gaps = report.dependency_gaps_for(
        "rotation_maker",
        ("weapon_enchantments:runtime_cadence",),
    )
    optimizer_gaps = report.dependency_gaps_for(
        "optimizer",
        ("weapon_enchantments:runtime_cadence",),
    )

    assert len(rotation_gaps) == 1
    assert len(optimizer_gaps) == 1
    assert rotation_gaps[0].blocking is True
    assert optimizer_gaps[0].blocking is True
