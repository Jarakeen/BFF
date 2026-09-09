from __future__ import annotations

from services.extreme_actual_heal_coverage_audit_service import (
    ExtremeActualHealCoverageAuditService,
)
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationService,
)
from services.extreme_healing_event_recipient_scope_service import (
    ExtremeHealingEventRecipientScopeService,
)


def _by_id():
    return {
        row.mechanic_id: row
        for row in ExtremeActualHealCoverageAuditService().items()
    }


def test_h1_audit_classifies_every_required_surface() -> None:
    service = ExtremeActualHealCoverageAuditService()
    rows = service.items()

    categories = {row.category for row in rows}
    assert set(service.REQUIRED_CATEGORIES) <= categories
    assert len({row.mechanic_id for row in rows}) == len(rows)
    assert {row.status for row in rows} <= {
        "implemented",
        "conditional",
        "unresolved",
        "irrelevant",
    }


def test_h1_audit_keeps_conditional_and_irrelevant_out_of_covered_count() -> None:
    service = ExtremeActualHealCoverageAuditService()
    rows = service.items()
    summary = service.summary()

    assert summary.denominator == sum(row.status != "irrelevant" for row in rows)
    assert summary.covered == sum(row.status == "implemented" for row in rows)
    assert summary.conditional > 0
    assert summary.irrelevant > 0
    assert summary.coverage_fraction == summary.covered / summary.denominator


def test_h1_audit_keeps_dragon_blood_recipient_identity_unresolved() -> None:
    rows = _by_id()
    dragon_blood = rows["dragon_blood_component_recipient_identity"]

    assert dragon_blood.status == "unresolved"
    assert "blood of the elder dragon" in {
        name.casefold()
        for name in ExtremeHealingEventRecipientScopeService.MULTI_RECIPIENT_DISTINCT_SCALING
    }
    assert "coagulating blood" in {
        name.casefold()
        for name in ExtremeHealingEventRecipientScopeService.MULTI_RECIPIENT_DISTINCT_SCALING
    }
    assert "dragon_blood_component_recipient_identity" in (
        ExtremeActualHealCoverageAuditService().summary().blocker_ids
    )


def test_h1_audit_reflects_existing_optimizer_scope_boundaries() -> None:
    rows = _by_id()
    search_scope = " | ".join(ExtremeActualHealOptimizationService.SEARCH_SCOPE).casefold()
    omitted_scope = " | ".join(ExtremeActualHealOptimizationService.OMITTED_SCOPE).casefold()

    assert "verified healing cp" in search_scope
    assert rows["verified_healing_champion_points"].status == "implemented"
    assert "group-only buffs" in omitted_scope
    assert rows["external_group_buff_provenance"].status == "unresolved"
    assert "runtime conditional stacks/procs" in omitted_scope
    assert rows["runtime_stat_buff_windows"].status == "conditional"


def test_h1_audit_summary_is_deterministic() -> None:
    service = ExtremeActualHealCoverageAuditService()

    first = service.summary()
    second = service.summary()

    assert first == second
    assert first.blocker_ids == tuple(
        row.mechanic_id
        for row in service.items()
        if row.status in {"conditional", "unresolved"}
    )
