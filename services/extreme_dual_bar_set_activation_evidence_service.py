from __future__ import annotations

"""Explain bar-local gear-set activation for one legal Extreme two-bar state.

This service owns no set math.  It materializes the already-proven dual-bar gear
state, asks ``GearStatInputResolver`` for canonical set counts on each bar, and
joins those counts to canonical ``gear_set_bonus`` breakpoints.

The result distinguishes always-active, front-only, back-only, and inactive set
bonus thresholds.  Arena-style weapon packages are identified structurally from
the shared slot-eligibility contract: max equip count two, weapon evidence
present, and no armor/jewelry/other equip evidence.  No set names are special
cased.
"""

from dataclasses import dataclass
from enum import Enum

from minmax.gear_set_repository import GearSetRepository
from minmax.gear_stat_inputs import GearStatInputResolver
from models.build_model import PlayerBuild
from services.extreme_dual_bar_gear_state_service import (
    ExtremeDualBarGearState,
    ExtremeDualBarGearStateService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityCatalog,
)


class ExtremeDualBarSetActivationScope(str, Enum):
    BOTH = "both"
    FRONT_ONLY = "front_only"
    BACK_ONLY = "back_only"
    INACTIVE = "inactive"


@dataclass(frozen=True)
class ExtremeDualBarSetActivationEvidence:
    set_id: int
    set_name: str
    category: str
    front_count: int
    back_count: int
    front_active_breakpoints: tuple[int, ...]
    back_active_breakpoints: tuple[int, ...]
    activation_scope: ExtremeDualBarSetActivationScope
    weapon_only_two_piece: bool

    @property
    def highest_front_breakpoint(self) -> int:
        return max(self.front_active_breakpoints, default=0)

    @property
    def highest_back_breakpoint(self) -> int:
        return max(self.back_active_breakpoints, default=0)


@dataclass(frozen=True)
class ExtremeDualBarSetActivationEvidenceCatalog:
    evidence: tuple[ExtremeDualBarSetActivationEvidence, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        return bool(self.evidence) and not self.unresolved


class ExtremeDualBarSetActivationEvidenceService:
    """Project canonical set bonus activation across front and back bars."""

    def __init__(
        self,
        *,
        repository: GearSetRepository,
        eligibility: ExtremeNamedGearSetSlotEligibilityCatalog,
    ) -> None:
        self.repository = repository
        self.eligibility = eligibility

    @staticmethod
    def _scope(
        front_breakpoints: tuple[int, ...],
        back_breakpoints: tuple[int, ...],
    ) -> ExtremeDualBarSetActivationScope:
        front = bool(front_breakpoints)
        back = bool(back_breakpoints)
        if front and back:
            return ExtremeDualBarSetActivationScope.BOTH
        if front:
            return ExtremeDualBarSetActivationScope.FRONT_ONLY
        if back:
            return ExtremeDualBarSetActivationScope.BACK_ONLY
        return ExtremeDualBarSetActivationScope.INACTIVE

    @staticmethod
    def _active_breakpoints(
        breakpoints: tuple[int, ...],
        count: int,
    ) -> tuple[int, ...]:
        return tuple(value for value in breakpoints if value <= int(count))

    @staticmethod
    def _weapon_only_two_piece(eligibility) -> bool:
        return bool(
            eligibility is not None
            and int(eligibility.max_equip_count) == 2
            and eligibility.weapon_types
            and not eligibility.armor_slots
            and not eligibility.jewelry_slots
            and not eligibility.other_equip_types
        )

    def build(
        self,
        state: ExtremeDualBarGearState,
        *,
        build: PlayerBuild | None = None,
    ) -> ExtremeDualBarSetActivationEvidenceCatalog:
        errors = list(ExtremeDualBarGearStateService.validate(state))
        if errors:
            return ExtremeDualBarSetActivationEvidenceCatalog(
                evidence=(),
                unresolved=tuple(errors),
            )

        candidate = ExtremeDualBarGearStateService.materialize(build or PlayerBuild(), state)
        front_counts = GearStatInputResolver.equipped_set_counts(candidate, active_bar="front")
        back_counts = GearStatInputResolver.equipped_set_counts(candidate, active_bar="back")
        names = tuple(sorted(set(front_counts) | set(back_counts), key=lambda value: value.casefold()))

        evidence: list[ExtremeDualBarSetActivationEvidence] = []
        unresolved: list[str] = list(self.eligibility.unresolved)

        for name in names:
            gear_set = self.repository.get_set(name)
            if gear_set is None:
                unresolved.append(f"Dual-bar gear set activation has unknown canonical set: {name}")
                continue

            bonuses = tuple(self.repository.get_bonuses(gear_set.id))
            breakpoints = tuple(sorted({int(row.piece_count) for row in bonuses if int(row.piece_count) > 0}))
            if not breakpoints:
                unresolved.append(f"Gear set {gear_set.name} has no canonical bonus breakpoints")

            front_count = int(front_counts.get(name, 0))
            back_count = int(back_counts.get(name, 0))
            front_active = self._active_breakpoints(breakpoints, front_count)
            back_active = self._active_breakpoints(breakpoints, back_count)
            slot_row = self.eligibility.by_set_id(int(gear_set.id))
            if slot_row is None:
                unresolved.append(
                    f"Gear set {gear_set.name} has no named slot-eligibility evidence for dual-bar activation"
                )

            evidence.append(
                ExtremeDualBarSetActivationEvidence(
                    set_id=int(gear_set.id),
                    set_name=str(gear_set.name),
                    category=str(gear_set.category or ""),
                    front_count=front_count,
                    back_count=back_count,
                    front_active_breakpoints=front_active,
                    back_active_breakpoints=back_active,
                    activation_scope=self._scope(front_active, back_active),
                    weapon_only_two_piece=self._weapon_only_two_piece(slot_row),
                )
            )

        evidence.sort(key=lambda row: (row.set_name.casefold(), row.set_id))
        return ExtremeDualBarSetActivationEvidenceCatalog(
            evidence=tuple(evidence),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )
