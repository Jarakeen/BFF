from __future__ import annotations

"""Compose complete sustained-DPS named-gear topology branches into legal two-bar states."""

from dataclasses import dataclass

from services.extreme_dual_bar_gear_state_catalog_service import (
    ExtremeDualBarGearStateCatalog,
    ExtremeDualBarGearStateCatalogService,
)
from services.extreme_sustained_dps_gear_topology_realization_service import (
    ExtremeSustainedDPSGearTopologyRealization,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSDualBarGearFrontier:
    expected_topology_count: int
    supplied_topology_count: int
    proven_topology_count: int
    active_snapshot_count: int
    dual_bar_state_count: int
    compatible_pairs_reviewed: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]
    catalog: ExtremeDualBarGearStateCatalog


class ExtremeSustainedDPSDualBarGearFrontierService:
    """Require complete topology coverage before proving the two-bar gear denominator."""

    @classmethod
    def build(
        cls,
        branches: tuple[ExtremeSustainedDPSGearTopologyRealization, ...],
        *,
        expected_topology_count: int,
    ) -> ExtremeSustainedDPSDualBarGearFrontier:
        expected = int(expected_topology_count)
        if expected <= 0:
            raise ValueError("expected_topology_count must be positive")

        unresolved: list[str] = []
        by_index: dict[int, ExtremeSustainedDPSGearTopologyRealization] = {}
        for branch in branches:
            index = int(branch.topology_index)
            if index < 0 or index >= expected:
                unresolved.append(
                    f"Gear topology branch index {index} lies outside expected 0..{expected - 1}"
                )
                continue
            if index in by_index:
                unresolved.append(f"Duplicate gear topology branch index: {index}")
                continue
            by_index[index] = branch

        missing = tuple(index for index in range(expected) if index not in by_index)
        if missing:
            unresolved.append(
                "Missing sustained-DPS gear topology branch(es): "
                + ", ".join(str(index) for index in missing)
            )

        proven_count = 0
        realizations = []
        for index in sorted(by_index):
            branch = by_index[index]
            if branch.denominator_proven:
                proven_count += 1
            else:
                unresolved.extend(
                    f"Topology {index}: {item}"
                    for item in branch.unresolved
                )
                if not branch.unresolved:
                    unresolved.append(f"Topology {index}: branch denominator is not proven")
            realizations.extend(branch.result.realizations)

        source_denominator_proven = (
            len(by_index) == expected
            and proven_count == expected
            and not unresolved
        )

        catalog = ExtremeDualBarGearStateCatalogService.build(
            tuple(realizations),
            source_denominator_proven=source_denominator_proven,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
        final_unresolved = tuple(
            dict.fromkeys((*unresolved, *catalog.unresolved))
        )

        return ExtremeSustainedDPSDualBarGearFrontier(
            expected_topology_count=expected,
            supplied_topology_count=len(by_index),
            proven_topology_count=proven_count,
            active_snapshot_count=int(catalog.active_snapshots_reviewed),
            dual_bar_state_count=len(catalog.states),
            compatible_pairs_reviewed=int(catalog.compatible_pairs_reviewed),
            denominator_proven=bool(catalog.denominator_proven and not final_unresolved),
            evidence=(
                f"Expected topology branches: {expected}",
                f"Supplied/proven topology branches: {len(by_index)}/{proven_count}",
                f"Unique active snapshots reviewed: {catalog.active_snapshots_reviewed}",
                f"Compatible front/back pairs reviewed: {catalog.compatible_pairs_reviewed}",
                f"Legal two-bar gear states: {len(catalog.states)}",
                "Front/back pairing requires identical shared body/jewelry assignments",
                "Bar activation legality remains canonical, including one-bar Oakensoul states",
            ),
            unresolved=final_unresolved,
            catalog=catalog,
        )


__all__ = [
    "ExtremeSustainedDPSDualBarGearFrontier",
    "ExtremeSustainedDPSDualBarGearFrontierService",
]
