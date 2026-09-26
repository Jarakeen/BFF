from __future__ import annotations

"""Concrete indexed-axis adapters for generated sustained-DPS gear refinement.

A proven dual-bar gear catalog is selected first because compatibility is a global fact
across the closed named-topology denominator. Armor, jewelry, and weapon traits/enchants
then mutate the same evolving materialized build in order, preventing convenience
snapshots from erasing previously selected gear-axis state.
"""

from dataclasses import dataclass, replace

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_dual_bar_gear_state_service import ExtremeDualBarGearState
from services.extreme_sustained_dps_armor_trait_enchant_frontier_service import (
    ExtremeSustainedDPSArmorTraitEnchantCandidate,
    ExtremeSustainedDPSArmorTraitEnchantFrontierService,
)
from services.extreme_sustained_dps_cross_axis_context_service import (
    ExtremeSustainedDPSCrossAxisContext,
    ExtremeSustainedDPSCrossAxisContextService,
)
from services.extreme_sustained_dps_dual_bar_gear_frontier_service import (
    ExtremeSustainedDPSDualBarGearFrontier,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSIndexedFrontierAxis,
)
from services.extreme_sustained_dps_jewelry_frontier_service import (
    ExtremeSustainedDPSJewelryCandidate,
    ExtremeSustainedDPSJewelryFrontierService,
)
from services.extreme_sustained_dps_weapon_frontier_service import (
    ExtremeSustainedDPSWeaponCandidate,
    ExtremeSustainedDPSWeaponFrontierService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedGearAxisState:
    baseline_build: PlayerBuild
    progression: CharacterProgression
    dual_bar_frontier: ExtremeSustainedDPSDualBarGearFrontier
    gear_state: ExtremeDualBarGearState | None = None
    context: ExtremeSustainedDPSCrossAxisContext | None = None
    armor: ExtremeSustainedDPSArmorTraitEnchantCandidate | None = None
    jewelry: ExtremeSustainedDPSJewelryCandidate | None = None
    weapon: ExtremeSustainedDPSWeaponCandidate | None = None

    @property
    def current_build(self) -> PlayerBuild:
        if self.context is not None:
            return self.context.build
        return self.baseline_build

    @property
    def complete(self) -> bool:
        return (
            self.gear_state is not None
            and self.context is not None
            and self.armor is not None
            and self.jewelry is not None
            and self.weapon is not None
        )


class ExtremeSustainedDPSGeneratedGearAxisAdapterService:
    """Adapt proven dual-bar gear plus trait/enchant frontiers into tree axes."""

    def __init__(
        self,
        *,
        context_service: ExtremeSustainedDPSCrossAxisContextService | object,
        armor: ExtremeSustainedDPSArmorTraitEnchantFrontierService | object = (
            ExtremeSustainedDPSArmorTraitEnchantFrontierService
        ),
        jewelry: ExtremeSustainedDPSJewelryFrontierService | object,
        weapon: ExtremeSustainedDPSWeaponFrontierService | object,
    ) -> None:
        self.context_service = context_service
        self.armor = armor
        self.jewelry = jewelry
        self.weapon = weapon

    @staticmethod
    def _proven_count(
        frontier: object,
        label: str,
        *,
        count_field: str = "candidate_count",
    ) -> int:
        raw_count = getattr(frontier, count_field, 0)
        if isinstance(raw_count, bool) or not isinstance(raw_count, int):
            raise TypeError(f"{label} candidate count must be an integer")
        count = raw_count
        unresolved = getattr(frontier, "unresolved", ())
        if not isinstance(unresolved, tuple):
            raise TypeError(f"{label} unresolved evidence must be a tuple")
        denominator_proven = getattr(frontier, "denominator_proven", False)
        if not isinstance(denominator_proven, bool):
            raise TypeError(f"{label} denominator proof flag must be boolean")
        if not denominator_proven:
            detail = "; ".join(str(item) for item in unresolved if str(item))
            raise ValueError(
                f"{label} denominator is unresolved"
                + (f": {detail}" if detail else "")
            )
        if count <= 0:
            raise ValueError(f"{label} denominator is empty")
        return count

    @staticmethod
    def _require_context(
        state: ExtremeSustainedDPSGeneratedGearAxisState,
    ) -> ExtremeSustainedDPSCrossAxisContext:
        if state.context is None:
            raise ValueError("generated gear refinement requires a selected dual-bar gear state")
        return state.context

    @staticmethod
    def _with_build(
        context: ExtremeSustainedDPSCrossAxisContext,
        build: PlayerBuild,
    ) -> ExtremeSustainedDPSCrossAxisContext:
        return replace(context, build=build)

    def _dual_count(
        self,
        state: ExtremeSustainedDPSGeneratedGearAxisState,
    ) -> int:
        return self._proven_count(
            state.dual_bar_frontier,
            "dual-bar gear frontier",
            count_field="dual_bar_state_count",
        )

    def _dual_at(
        self,
        state: ExtremeSustainedDPSGeneratedGearAxisState,
        index: int,
    ) -> ExtremeSustainedDPSGeneratedGearAxisState:
        frontier = state.dual_bar_frontier
        target = int(index)
        count = self._dual_count(state)
        if target < 0 or target >= count:
            raise IndexError("dual-bar gear state index out of range")
        gear_state = frontier.catalog.states[target]
        context = self.context_service.compose(
            state.baseline_build,
            state.progression,
            gear_state=gear_state,
        )
        return replace(state, gear_state=gear_state, context=context)

    def _armor_count(
        self,
        state: ExtremeSustainedDPSGeneratedGearAxisState,
    ) -> int:
        self._require_context(state)
        return self._proven_count(
            self.armor.frontier(state.current_build),
            "armor trait/enchant frontier",
        )

    def _armor_at(
        self,
        state: ExtremeSustainedDPSGeneratedGearAxisState,
        index: int,
    ) -> ExtremeSustainedDPSGeneratedGearAxisState:
        context = self._require_context(state)
        candidate = self.armor.candidate_at(state.current_build, int(index))
        return replace(
            state,
            armor=candidate,
            context=self._with_build(context, candidate.build),
        )

    def _jewelry_count(
        self,
        state: ExtremeSustainedDPSGeneratedGearAxisState,
    ) -> int:
        self._require_context(state)
        return self._proven_count(
            self.jewelry.frontier(state.current_build),
            "jewelry frontier",
        )

    def _jewelry_at(
        self,
        state: ExtremeSustainedDPSGeneratedGearAxisState,
        index: int,
    ) -> ExtremeSustainedDPSGeneratedGearAxisState:
        context = self._require_context(state)
        candidate = self.jewelry.candidate_at(state.current_build, int(index))
        return replace(
            state,
            jewelry=candidate,
            context=self._with_build(context, candidate.build),
        )

    def _weapon_count(
        self,
        state: ExtremeSustainedDPSGeneratedGearAxisState,
    ) -> int:
        self._require_context(state)
        return self._proven_count(
            self.weapon.frontier(state.current_build),
            "weapon frontier",
        )

    def _weapon_at(
        self,
        state: ExtremeSustainedDPSGeneratedGearAxisState,
        index: int,
    ) -> ExtremeSustainedDPSGeneratedGearAxisState:
        context = self._require_context(state)
        candidate = self.weapon.candidate_at(state.current_build, int(index))
        return replace(
            state,
            weapon=candidate,
            context=self._with_build(context, candidate.build),
        )

    def root(
        self,
        build: PlayerBuild,
        progression: CharacterProgression,
        *,
        dual_bar_frontier: ExtremeSustainedDPSDualBarGearFrontier,
    ) -> ExtremeSustainedDPSGeneratedGearAxisState:
        return ExtremeSustainedDPSGeneratedGearAxisState(
            baseline_build=build,
            progression=progression,
            dual_bar_frontier=dual_bar_frontier,
        )

    def axes(self) -> tuple[ExtremeSustainedDPSIndexedFrontierAxis, ...]:
        return (
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Dual Bar Gear",
                candidate_count=self._dual_count,
                candidate_at=self._dual_at,
                canonical_axes=("gear_topology", "named_gear_realization"),
            ),
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Armor Traits and Enchants",
                candidate_count=self._armor_count,
                candidate_at=self._armor_at,
                canonical_axes=("armor_traits", "armor_enchants"),
            ),
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Jewelry Traits and Enchants",
                candidate_count=self._jewelry_count,
                candidate_at=self._jewelry_at,
                canonical_axes=("jewelry_traits", "jewelry_enchants"),
            ),
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Weapon Traits and Enchants",
                candidate_count=self._weapon_count,
                candidate_at=self._weapon_at,
                canonical_axes=("weapon_types", "weapon_traits", "weapon_enchants"),
            ),
        )


__all__ = [
    "ExtremeSustainedDPSGeneratedGearAxisAdapterService",
    "ExtremeSustainedDPSGeneratedGearAxisState",
]
