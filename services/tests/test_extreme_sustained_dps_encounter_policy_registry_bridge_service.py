from __future__ import annotations

from types import SimpleNamespace

from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from services.extreme_sustained_dps_encounter_policy_registry_bridge_service import (
    ExtremeSustainedDPSEncounterPolicyRegistryBridgeService,
    ExtremeSustainedDPSEncounterThresholdDemandProjection,
)


def _demand(name):
    return RotationDemandWindow(
        name=name,
        start_seconds=5.0,
        end_seconds=8.0,
        kind=RotationDemandKind.DAMAGE,
        pattern=RotationDemandPattern.BURST,
    )


class _Registry:
    def __init__(self, entry):
        self.entry = entry

    def entry_for(self, encounter_id):
        assert encounter_id == "encounter:boss"
        return self.entry


class _Guide:
    def get(self, encounter_id):
        return SimpleNamespace(encounter_id=encounter_id)


class _Projector:
    def __init__(self, *, unresolved=()):
        self.unresolved = tuple(unresolved)
        self.calls = []

    def project(self, *, guide, policies):
        self.calls.append((guide, policies))
        return SimpleNamespace(
            demands=(_demand("Clock Burst"),),
            unresolved=self.unresolved,
        )


def _service(entry, *, projector=None):
    return ExtremeSustainedDPSEncounterPolicyRegistryBridgeService(
        registry=_Registry(entry),
        guide_service=_Guide(),
        demand_service=projector or _Projector(),
    )


def test_reviewed_clock_policy_becomes_one_proven_encounter_choice() -> None:
    entry = SimpleNamespace(
        clock_policies=(object(),),
        threshold_policies=(),
        review_blockers=(),
    )
    result = _service(entry).build("encounter:boss")

    assert result.denominator_proven is True
    assert result.candidate_count == 1
    assert result.choices[0].policy_id == "encounter:encounter:boss"
    assert tuple(row.name for row in result.choices[0].demands) == (
        "Clock Burst",
    )


def test_explicitly_empty_reviewed_policy_is_proven_no_demand_choice() -> None:
    entry = SimpleNamespace(
        clock_policies=(),
        threshold_policies=(),
        review_blockers=(),
    )
    result = _service(entry).build("encounter:boss")

    assert result.denominator_proven is True
    assert result.choices[0].demands == ()
    assert any(
        "explicitly contains no rotation demands" in row
        for row in result.choices[0].evidence
    )


def test_missing_registry_entry_keeps_encounter_policy_open() -> None:
    result = _service(None).build("encounter:boss")

    assert result.denominator_proven is False
    assert any(
        "No reviewed Rotation encounter-demand policy" in row
        for row in result.unresolved
    )


def test_review_blocker_keeps_encounter_policy_open() -> None:
    entry = SimpleNamespace(
        clock_policies=(),
        threshold_policies=(),
        review_blockers=(
            SimpleNamespace(
                key="strategy",
                needed_evidence="review exact mechanic response",
            ),
        ),
    )
    result = _service(entry).build("encounter:boss")

    assert result.denominator_proven is False
    assert any("strategy" in row for row in result.unresolved)


def test_threshold_policy_requires_proven_clock_projection() -> None:
    entry = SimpleNamespace(
        clock_policies=(),
        threshold_policies=(object(),),
        review_blockers=(),
    )
    service = _service(entry)

    open_result = service.build("encounter:boss")
    assert open_result.denominator_proven is False
    assert any("threshold-to-clock" in row for row in open_result.unresolved)

    closed_result = service.build(
        "encounter:boss",
        threshold_projection=ExtremeSustainedDPSEncounterThresholdDemandProjection(
            demands=(_demand("Threshold Burst"),),
            denominator_proven=True,
            source="explicit health trajectory projection",
        ),
    )
    assert closed_result.denominator_proven is True
    assert tuple(row.name for row in closed_result.choices[0].demands) == (
        "Threshold Burst",
    )


def test_unresolved_clock_projection_keeps_policy_open() -> None:
    entry = SimpleNamespace(
        clock_policies=(object(),),
        threshold_policies=(),
        review_blockers=(),
    )
    result = _service(
        entry,
        projector=_Projector(unresolved=("clock fact unresolved",)),
    ).build("encounter:boss")

    assert result.denominator_proven is False
    assert any("clock fact unresolved" in row for row in result.unresolved)
