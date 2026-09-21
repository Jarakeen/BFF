from __future__ import annotations

from types import SimpleNamespace

from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetCountTopology,
)
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetTopologyRealizationResult,
)
from services.extreme_sustained_dps_gear_topology_realization_service import (
    ExtremeSustainedDPSGearTopologyRealizationService,
)


class _TopologyService:
    def topology_at(self, index):
        assert index == 0
        return ExtremeGearSetCountTopology(counts=(5, 5, 2), unused_units=0)


class _RealizationService:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def realize_topology(self, topology, *, max_assignments=None):
        self.calls.append((topology.signature, max_assignments))
        return self.result


def _result(*, realized=2, considered=3, rejected=1, truncated=False, unresolved=()):
    topology = ExtremeGearSetCountTopology(counts=(5, 5, 2), unused_units=0)
    realizations = tuple(SimpleNamespace() for _ in range(realized))
    return ExtremeNamedGearSetTopologyRealizationResult(
        topology=topology,
        realizations=realizations,
        assignments_considered=considered,
        assignments_rejected=rejected,
        truncated=truncated,
        unresolved=tuple(unresolved),
    )


def test_full_topology_realization_can_prove_branch_denominator() -> None:
    inner = _RealizationService(_result())
    service = ExtremeSustainedDPSGearTopologyRealizationService(
        topology_service=_TopologyService(),
        realization_service=inner,
    )

    result = service.realize(0)

    assert result.topology_signature == "5+5+2|unused:0"
    assert result.assignments_considered == 3
    assert result.assignments_realized == 2
    assert result.assignments_rejected == 1
    assert result.denominator_proven is True
    assert result.unresolved == ()


def test_truncated_topology_realization_is_explicitly_unproven() -> None:
    inner = _RealizationService(_result(realized=1, considered=1, rejected=0, truncated=True))
    service = ExtremeSustainedDPSGearTopologyRealizationService(
        topology_service=_TopologyService(),
        realization_service=inner,
    )

    result = service.realize(0, max_assignments=1)

    assert inner.calls == [("5+5+2|unused:0", 1)]
    assert result.truncated is True
    assert result.denominator_proven is False
    assert any("truncated" in row.casefold() for row in result.unresolved)


def test_unresolved_canonical_evidence_keeps_branch_open() -> None:
    service = ExtremeSustainedDPSGearTopologyRealizationService(
        topology_service=_TopologyService(),
        realization_service=_RealizationService(
            _result(unresolved=("slot eligibility unresolved",))
        ),
    )

    result = service.realize(0)

    assert result.denominator_proven is False
    assert "slot eligibility unresolved" in result.unresolved


def test_exhaustive_branch_with_no_physical_witness_is_proven_empty() -> None:
    service = ExtremeSustainedDPSGearTopologyRealizationService(
        topology_service=_TopologyService(),
        realization_service=_RealizationService(
            _result(realized=0, considered=4, rejected=4)
        ),
    )

    result = service.realize(0)

    assert result.denominator_proven is True
    assert result.unresolved == ()
    assert any("proven empty" in row.casefold() for row in result.evidence)
