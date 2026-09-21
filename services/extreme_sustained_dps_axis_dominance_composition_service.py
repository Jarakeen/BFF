from __future__ import annotations

"""Compose proof coverage over canonical generated sustained-DPS mutation axes.

This service owns axis identity and coverage composition only. It does not calculate
numeric optimistic multipliers or damage. Independent proofs may cover disjoint or
overlapping axes; their coverage is unioned. A composed dominance proof is complete
only when every required open axis is covered and no contributor remains unresolved.
"""

from dataclasses import dataclass

from services.extreme_sustained_dps_action_upper_bound_service import (
    ExtremeSustainedDPSActionDominanceProof,
)


CANONICAL_SUSTAINED_DPS_MUTATION_AXES = (
    "race",
    "class_route",
    "attributes",
    "gear_topology",
    "named_gear_realization",
    "armor_traits",
    "armor_enchants",
    "jewelry_traits",
    "jewelry_enchants",
    "weapon_types",
    "weapon_traits",
    "weapon_enchants",
    "mundus",
    "food",
    "potion_selection",
    "champion_points",
    "passive_ranks",
    "skill_bars",
    "rotation_order",
    "light_attack_weave",
    "ultimate_policy",
    "potion_timing_policy",
    "execute_policy",
    "heavy_attack_policy",
    "runtime_state",
    "encounter_policy",
)


@dataclass(frozen=True)
class ExtremeSustainedDPSAxisCoverageProof:
    source: str
    dominated_axes: tuple[str, ...]
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        source = str(self.source or "").strip()
        if not source:
            raise ValueError("axis coverage proof requires source")
        canonical = {axis.casefold(): axis for axis in CANONICAL_SUSTAINED_DPS_MUTATION_AXES}
        values: list[str] = []
        unknown: list[str] = []
        for raw in self.dominated_axes:
            key = str(raw or "").strip().casefold()
            if not key:
                continue
            axis = canonical.get(key)
            if axis is None:
                unknown.append(str(raw).strip())
            elif axis not in values:
                values.append(axis)
        unresolved = [
            str(item).strip()
            for item in self.unresolved
            if str(item).strip()
        ]
        if unknown:
            unresolved.append(
                "Unknown sustained-DPS mutation axis coverage: "
                + ", ".join(sorted(set(unknown), key=str.casefold))
            )
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "dominated_axes", tuple(values))
        object.__setattr__(
            self,
            "unresolved",
            tuple(dict.fromkeys(unresolved)),
        )


@dataclass(frozen=True)
class ExtremeSustainedDPSAxisDominanceComposition:
    candidate_key: str
    required_axes: tuple[str, ...]
    dominated_axes: tuple[str, ...]
    missing_axes: tuple[str, ...]
    contributing_sources: tuple[str, ...]
    proof: ExtremeSustainedDPSActionDominanceProof
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSAxisDominanceCompositionService:
    """Union proof coverage and emit a canonical action-dominance coverage proof."""

    @classmethod
    def compose(
        cls,
        candidate_key: str,
        *,
        required_axes: tuple[str, ...],
        proofs: tuple[ExtremeSustainedDPSAxisCoverageProof, ...],
        optimistic_multiplier: float = 1.0,
        optimistic_upper_damage: float | None = None,
    ) -> ExtremeSustainedDPSAxisDominanceComposition:
        key = str(candidate_key or "").strip()
        if not key:
            raise ValueError("axis dominance composition requires candidate_key")

        canonical = {axis.casefold(): axis for axis in CANONICAL_SUSTAINED_DPS_MUTATION_AXES}
        required: list[str] = []
        unresolved: list[str] = []
        unknown_required: list[str] = []
        for raw in required_axes:
            normalized = str(raw or "").strip().casefold()
            if not normalized:
                continue
            axis = canonical.get(normalized)
            if axis is None:
                unknown_required.append(str(raw).strip())
            elif axis not in required:
                required.append(axis)
        if unknown_required:
            unresolved.append(
                "Unknown required sustained-DPS mutation axis: "
                + ", ".join(sorted(set(unknown_required), key=str.casefold))
            )

        dominated: list[str] = []
        sources: list[str] = []
        for proof in proofs:
            sources.append(proof.source)
            unresolved.extend(
                f"{proof.source}: {item}"
                for item in proof.unresolved
            )
            for axis in proof.dominated_axes:
                if axis not in dominated:
                    dominated.append(axis)

        dominated_set = {axis.casefold() for axis in dominated}
        missing = tuple(
            axis
            for axis in required
            if axis.casefold() not in dominated_set
        )

        deduped = tuple(
            dict.fromkeys(
                item
                for item in unresolved
                if str(item).strip()
            )
        )
        action_proof = ExtremeSustainedDPSActionDominanceProof(
            candidate_key=key,
            dominated_axes=tuple(dominated),
            required_axes=tuple(required),
            optimistic_multiplier=float(optimistic_multiplier),
            optimistic_upper_damage=optimistic_upper_damage,
            source="; ".join(dict.fromkeys(sources)),
            unresolved=deduped,
        )

        return ExtremeSustainedDPSAxisDominanceComposition(
            candidate_key=key,
            required_axes=tuple(required),
            dominated_axes=tuple(dominated),
            missing_axes=missing,
            contributing_sources=tuple(dict.fromkeys(sources)),
            proof=action_proof,
            evidence=(
                f"Required canonical mutation axes: {len(required)}",
                f"Dominated canonical mutation axes: {len(dominated)}",
                f"Missing mutation axes: {len(missing)}",
                f"Dominance proof contributors: {len(tuple(dict.fromkeys(sources)))}",
                "Axis coverage is composed by set union only; numeric optimism remains external",
            ),
            unresolved=deduped,
        )


__all__ = [
    "CANONICAL_SUSTAINED_DPS_MUTATION_AXES",
    "ExtremeSustainedDPSAxisCoverageProof",
    "ExtremeSustainedDPSAxisDominanceComposition",
    "ExtremeSustainedDPSAxisDominanceCompositionService",
]
