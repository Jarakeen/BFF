from __future__ import annotations

"""Proof-safe armor-weight states for Extreme max-resource records.

For max Health/Magicka/Stamina, armor weight has no direct resource contribution
in the currently reviewed canonical armor passives.  Its only reviewed max-resource
continuation is Undaunted Mettle, whose value depends on the number of distinct
armor types equipped rather than the exact per-slot distribution.

This service therefore enumerates all legal seven-slot Light/Medium/Heavy loadouts
and preserves one deterministic concrete witness for each distinct armor-type count
(1, 2, or 3).  It does not grant Undaunted Mettle or any other passive; passive
ownership remains a separate Extreme denominator axis.
"""

from dataclasses import dataclass
from itertools import product

from models.build_model import ARMOR_SLOTS, PlayerBuild


_WEIGHTS = ("Heavy", "Light", "Medium")
_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


@dataclass(frozen=True)
class ExtremeArmorResourceWeightState:
    objective_key: str
    weights: tuple[tuple[str, str], ...]

    @property
    def armor_type_count(self) -> int:
        return len({weight for _, weight in self.weights})

    @property
    def light_pieces(self) -> int:
        return sum(1 for _, weight in self.weights if weight == "Light")

    @property
    def medium_pieces(self) -> int:
        return sum(1 for _, weight in self.weights if weight == "Medium")

    @property
    def heavy_pieces(self) -> int:
        return sum(1 for _, weight in self.weights if weight == "Heavy")

    @property
    def identity(self) -> tuple[tuple[str, str], ...]:
        return self.weights


@dataclass(frozen=True)
class ExtremeArmorResourceWeightStateCatalog:
    objective_key: str
    states: tuple[ExtremeArmorResourceWeightState, ...]
    raw_loadouts_reviewed: int
    dominated_loadouts_pruned: int
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        return (
            tuple(state.armor_type_count for state in self.states) == (1, 2, 3)
            and not self.unresolved
        )


class ExtremeArmorResourceWeightStateService:
    """Reduce legal seven-piece armor weights by distinct armor-type count."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    @classmethod
    def build(cls, objective_key: str) -> ExtremeArmorResourceWeightStateCatalog:
        key = str(objective_key or "").strip().casefold()
        if key not in cls.SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme resource armor-weight objective: {objective_key!r}")

        witnesses: dict[int, tuple[tuple[str, str], ...]] = {}
        raw = 0
        for values in product(_WEIGHTS, repeat=len(ARMOR_SLOTS)):
            raw += 1
            weights = tuple(zip(ARMOR_SLOTS, values))
            armor_type_count = len(set(values))
            incumbent = witnesses.get(armor_type_count)
            if incumbent is None or weights < incumbent:
                witnesses[armor_type_count] = weights

        states = tuple(
            ExtremeArmorResourceWeightState(
                objective_key=key,
                weights=witnesses[count],
            )
            for count in sorted(witnesses)
        )
        unresolved: list[str] = []
        if tuple(witnesses) != (1, 2, 3):
            unresolved.append(
                "Resource armor-weight search did not preserve witnesses for all 1/2/3 armor-type counts"
            )

        return ExtremeArmorResourceWeightStateCatalog(
            objective_key=key,
            states=states,
            raw_loadouts_reviewed=raw,
            dominated_loadouts_pruned=max(0, raw - len(states)),
            unresolved=tuple(unresolved),
        )

    @staticmethod
    def materialize(
        build: PlayerBuild,
        state: ExtremeArmorResourceWeightState,
    ) -> PlayerBuild:
        candidate = PlayerBuild.from_dict(build.to_dict())
        seen: set[str] = set()
        for slot, weight in state.weights:
            if slot not in candidate.Armor:
                raise ValueError(f"unknown Extreme resource armor-weight slot: {slot!r}")
            if slot in seen:
                raise ValueError(f"duplicate Extreme resource armor-weight slot: {slot!r}")
            if weight not in {"Light", "Medium", "Heavy"}:
                raise ValueError(f"unknown Extreme armor weight: {weight!r}")
            seen.add(slot)
            candidate.Armor[slot]["Weight"] = weight

        if seen != set(candidate.Armor):
            missing = ", ".join(sorted(set(candidate.Armor) - seen))
            raise ValueError(
                f"Extreme resource armor-weight state does not cover all armor slots: {missing}"
            )
        return candidate
