from __future__ import annotations

from dataclasses import dataclass

import pytest

from minmax.fight_damage_trajectory import RaidDamageSegment
from minmax.rotation_demand_window import RotationDemandKind, RotationDemandPattern
from services.encounter_boss_guide import BossGuideTimelineFact, EncounterBossGuide
from services.encounter_threshold_rotation_demand_service import (
    EncounterThresholdRotationDemandPolicy,
)
from services.rotation_healer_demand_criteria_service import (
    RotationHealerDemandCriterion,
    RotationHealerDemandCriterionSourceKind,
)
from services.rotation_healer_encounter_criteria_provider import (
    RotationHealerEncounterCriteriaProjection,
)
from services.rotation_healer_encounter_demand_bundle_service import (
    RotationHealerEncounterDemandBundleService,
)


_DEMAND_NAME = "Xalvakka Phase 2 healing prep"


def _guide() -> EncounterBossGuide:
    return EncounterBossGuide(
        encounter_id="xalvakka",
        content_id="rockgrove",
        content_name="Rockgrove",
        name="Xalvakka",
        summary="",
        location="Rockgrove",
        species="Harvester",
        reaction="Hostile",
        health_record_present=True,
        health=(("hardmode", "214,233,024 (Hard Mode)"),),
        abilities=(),
        phases=(),
        structural_phases=(),
        timeline_facts=(
            BossGuideTimelineFact(
                fact_id=70,
                canonical_kind="phase",
                fact_type="phase",
                fact_key="phase_2",
                payload={"label": "Phase 2", "starts_at": "70%"},
                review_status="reviewed",
                evidence_count=2,
            ),
        ),
        source_url="",
        source_page_title="Xalvakka",
        source_revision_id="",
        retrieved_at="",
        source_license="",
    )


def _policy(name: str = _DEMAND_NAME) -> EncounterThresholdRotationDemandPolicy:
    return EncounterThresholdRotationDemandPolicy(
        fact_key="phase_2",
        threshold_fraction=0.70,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
        lead_seconds=3.0,
        window_seconds=2.0,
        target_count=12,
        name=name,
    )


class _CriteriaProvider:
    def __init__(self, criteria=(), unresolved=()):
        self.criteria = tuple(criteria)
        self.unresolved = tuple(unresolved)
        self.calls = []

    def criteria_for_encounter(self, *, encounter_id, reviewed_fact_ids=()):
        self.calls.append((encounter_id, tuple(reviewed_fact_ids)))
        return RotationHealerEncounterCriteriaProjection(
            encounter_id=encounter_id,
            criteria=self.criteria,
            unresolved=self.unresolved,
        )


def _damage_segments():
    return (
        RaidDamageSegment(
            0.0,
            None,
            2_000_000.0,
            "caller-supplied constant raid DPS test assumption",
        ),
    )


def test_real_threshold_window_projects_without_inventing_numeric_healer_criterion():
    provider = _CriteriaProvider()
    service = RotationHealerEncounterDemandBundleService(criteria_provider=provider)

    result = service.project(
        guide=_guide(),
        difficulty="hardmode",
        damage_segments=_damage_segments(),
        demand_policies=(_policy(),),
    )

    assert result.encounter_id == "xalvakka"
    assert result.difficulty == "hardmode"
    assert len(result.demands) == 1
    demand = result.demands[0]
    assert demand.name == _DEMAND_NAME
    assert demand.kind is RotationDemandKind.HEALING
    assert demand.target_count == 12
    assert result.criteria == ()
    assert result.unresolved == ()
    assert provider.calls == [("xalvakka", ())]

    point = result.threshold_projection.points[0]
    assert point.threshold_fraction == pytest.approx(0.70)
    assert point.time_seconds is not None
    assert demand.start_seconds == pytest.approx(point.time_seconds - 3.0)
    assert demand.end_seconds == pytest.approx(point.time_seconds + 2.0)


def test_matching_reviewed_criterion_is_included_in_selected_encounter_bundle():
    criterion = RotationHealerDemandCriterion(
        demand_name=_DEMAND_NAME,
        minimum_modeled_healing_per_demand_second=1250.0,
        source_kind=RotationHealerDemandCriterionSourceKind.VERIFIED_ENCOUNTER_EVIDENCE,
        provenance=("encounter_fact=xalvakka:healer_demand_criterion:phase_2",),
    )
    provider = _CriteriaProvider((criterion,))
    service = RotationHealerEncounterDemandBundleService(criteria_provider=provider)

    result = service.project(
        guide=_guide(),
        difficulty="hardmode",
        damage_segments=_damage_segments(),
        demand_policies=(_policy(),),
        reviewed_fact_ids=("xalvakka:healer_demand_criterion:phase_2",),
    )

    assert result.criteria == (criterion,)
    assert provider.calls == [
        (
            "xalvakka",
            ("xalvakka:healer_demand_criterion:phase_2",),
        )
    ]


def test_unrelated_encounter_criterion_does_not_leak_into_selected_demand_scope():
    unrelated = RotationHealerDemandCriterion(
        demand_name="Xalvakka execute burn",
        minimum_modeled_healing_per_demand_second=2000.0,
        source_kind=RotationHealerDemandCriterionSourceKind.VERIFIED_ENCOUNTER_EVIDENCE,
        provenance=("encounter_fact=xalvakka:healer_demand_criterion:execute",),
    )
    service = RotationHealerEncounterDemandBundleService(
        criteria_provider=_CriteriaProvider((unrelated,))
    )

    result = service.project(
        guide=_guide(),
        difficulty="hardmode",
        damage_segments=_damage_segments(),
        demand_policies=(_policy(),),
    )

    assert len(result.demands) == 1
    assert result.criteria == ()


def test_selected_reviewed_criterion_is_retained_when_clock_projection_is_unresolved():
    criterion = RotationHealerDemandCriterion(
        demand_name=_DEMAND_NAME,
        minimum_modeled_healing_per_demand_second=1250.0,
        source_kind=RotationHealerDemandCriterionSourceKind.VERIFIED_ENCOUNTER_EVIDENCE,
        provenance=("encounter_fact=xalvakka:healer_demand_criterion:phase_2",),
    )
    service = RotationHealerEncounterDemandBundleService(
        criteria_provider=_CriteriaProvider((criterion,))
    )

    result = service.project(
        guide=_guide(),
        difficulty="hardmode",
        damage_segments=(
            RaidDamageSegment(
                0.0,
                10.0,
                0.0,
                "no damage reaches threshold",
            ),
        ),
        demand_policies=(_policy(),),
    )

    assert result.demands == ()
    assert result.criteria == (criterion,)
    assert result.unresolved


def test_bundle_rejects_nonhealing_policy():
    policy = EncounterThresholdRotationDemandPolicy(
        fact_key="phase_2",
        threshold_fraction=0.70,
        kind=RotationDemandKind.SUPPORT,
        pattern=RotationDemandPattern.BURST,
        name="support prep",
    )
    service = RotationHealerEncounterDemandBundleService(
        criteria_provider=_CriteriaProvider()
    )

    with pytest.raises(ValueError, match="only healing demand policies"):
        service.project(
            guide=_guide(),
            difficulty="hardmode",
            damage_segments=_damage_segments(),
            demand_policies=(policy,),
        )
