from __future__ import annotations

import pytest

from minmax.skill_coefficients import SkillCoefficientTrace
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


def _trace(number: int, *, a: float, b: float, c: float) -> SkillCoefficientTrace:
    max_stat = 30000.0
    power = 5000.0
    resource_term = a * max_stat
    power_term = b * power
    before_r = resource_term + power_term + c
    return SkillCoefficientTrace(
        coefficient_number=number,
        coefficient_type="8",
        max_stat=max_stat,
        power=power,
        a=a,
        b=b,
        c=c,
        r=1.0,
        resource_term=resource_term,
        power_term=power_term,
        constant_term=c,
        before_r=before_r,
        final_value=before_r,
    )


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


def test_h1_audit_counts_proven_conditionals_as_supported_coverage() -> None:
    service = ExtremeActualHealCoverageAuditService()
    rows = service.items()
    summary = service.summary()

    assert summary.denominator == sum(row.status != "irrelevant" for row in rows)
    assert summary.covered == sum(
        row.status in {"implemented", "conditional"}
        for row in rows
        if row.status != "irrelevant"
    )
    assert summary.conditional > 0
    assert summary.irrelevant > 0
    assert summary.coverage_fraction == pytest.approx(
        summary.covered / summary.denominator
    )


def test_h1_audit_distinguishes_supported_conditionals_from_real_blockers() -> None:
    rows = _by_id()
    summary = ExtremeActualHealCoverageAuditService().summary()

    assert rows["runtime_stat_buff_windows"].status == "conditional"
    assert rows["explicit_target_health_conditionals"].status == "conditional"
    assert rows["runtime_stat_buff_windows"].is_supported
    assert rows["explicit_target_health_conditionals"].is_supported

    assert rows["reviewed_class_passive_families"].status == "implemented"
    assert rows["external_group_buff_provenance"].status == "unresolved"
    assert summary.blocker_ids == ("external_group_buff_provenance",)
    assert not summary.complete


def test_h1_audit_promotes_dragon_blood_after_exact_recipient_selection_is_implemented() -> None:
    rows = _by_id()
    dragon_blood = rows["dragon_blood_component_recipient_identity"]
    resolver = ExtremeHealingEventRecipientScopeService()
    resolved = resolver.resolve(
        ability_name="Blood of the Elder Dragon",
        heal_coefficient_numbers=(1, 2),
        coefficient_traces=(
            _trace(1, a=0.10, b=1.20, c=3.0),
            _trace(2, a=0.10 * 2.0 / 3.0, b=0.80, c=2.0),
        ),
    )

    assert resolved.single_recipient_safe
    assert resolved.selected_coefficient_numbers == (1,)
    assert resolved.unresolved == ()
    assert dragon_blood.status == "implemented"
    assert "blood of the elder dragon" in {
        name.casefold()
        for name in resolver.MULTI_RECIPIENT_DISTINCT_SCALING
    }
    assert "coagulating blood" in {
        name.casefold()
        for name in resolver.MULTI_RECIPIENT_DISTINCT_SCALING
    }
    assert "dragon_blood_component_recipient_identity" not in (
        ExtremeActualHealCoverageAuditService().summary().blocker_ids
    )


def test_h1_dragon_blood_missing_or_malformed_recipient_evidence_still_blocks() -> None:
    resolver = ExtremeHealingEventRecipientScopeService()

    missing = resolver.resolve(ability_name="Blood of the Elder Dragon")
    malformed = resolver.resolve(
        ability_name="Blood of the Elder Dragon",
        heal_coefficient_numbers=(1, 2),
        coefficient_traces=(
            _trace(1, a=0.10, b=1.20, c=3.0),
            _trace(2, a=0.07, b=0.80, c=2.0),
        ),
    )

    for result in (missing, malformed):
        assert not result.single_recipient_safe
        assert result.recipient_selection_required
        assert result.selected_coefficient_numbers is None
        assert result.unresolved


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
    assert "unreviewed skill-bar passive/proc families" in omitted_scope
    assert rows["reviewed_class_passive_families"].status == "implemented"


def test_h1_audit_summary_is_deterministic() -> None:
    service = ExtremeActualHealCoverageAuditService()

    first = service.summary()
    second = service.summary()

    assert first == second
    assert first.blocker_ids == tuple(
        row.mechanic_id
        for row in service.items()
        if row.status == "unresolved"
    )
