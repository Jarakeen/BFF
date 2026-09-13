from __future__ import annotations

"""Proof-safe armor-weight states for Extreme max-resource records.

For Max Magicka and Max Stamina, the only reviewed armor-weight continuation is
Undaunted Mettle, whose value depends on the number of distinct armor types equipped.
Those objectives may therefore preserve one deterministic witness for each 1/2/3-type
state.

Max Health has an additional reviewed continuation: Heavy Armor's Juggernaut, which
adds Max Health per Heavy piece.  Its proof signature must therefore preserve both
``armor_type_count`` and ``heavy_pieces``.  Collapsing Max Health by distinct type
count alone would merge states with different canonical Max Health values.

This service enumerates every legal seven-slot Light/Medium/Heavy loadout and keeps
one deterministic concrete witness per objective-relevant signature.  It owns no
resource arithmetic; canonical passive resolvers still apply Undaunted Mettle and
Juggernaut during scoring.
"""

from dataclasses import dataclass
from itertools import product

from models.build_model import ARMOR_SLOTS, PlayerBuild


_WEIGHTS = ("Heavy", "Light", "Medium")
_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")
_MAX_HEALTH = "max_health"


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

    @property
    def max_health_signature(self) -> tuple[int, int]:
        return (self.armor_type_count, self.heavy_pieces)


@dataclass(frozen=True)
class ExtremeArmorResourceWeightStateCatalog:
    objective_key: str
    states: tuple[ExtremeArmorResourceWeightState, ...]
    raw_loadouts_reviewed: int
    dominated_loadouts_pruned: int
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        if self.objective_key == _MAX_HEALTH:
            signatures = tuple(sorted(state.max_health_signature for state in self.states))
            expected = (
                (1, 0),
                (1, 7),
                (2, 0),
                (2, 1),
                (2, 2),
                (2, 3),
                (2, 4),
                (2, 5),
                (2, 6),
                (3, 1),
                (3, 2),
                (3, 3),
                (3, 4),
                (3, 5),
            )
            return signatures == expected and not self.unresolved
        return (
            tuple(state.armor_type_count for state in self.states) == (1, 2, 3)
            and not self.unresolved
        )


class ExtremeArmorResourceWeightStateService:
    """Reduce legal seven-piece armor weights by objective-relevant semantics."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    @classmethod
    def build(cls, objective_key: str) -> ExtremeArmorResourceWeightStateCatalog:
        key = str(objective_key or "").strip().casefold()
        if key not in cls.SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme resource armor-weight objective: {objective_key!r}")

        witnesses: dict[object, tuple[tuple[str, str], ...]] = {}
        raw = 0
        source_signatures: set[object] = set()
        for values in product(_WEIGHTS, repeat=len(ARMOR_SLOTS)):
            raw += 1
            weights = tuple(zip(ARMOR_SLOTS, values))
            armor_type_count = len(set(values))
            heavy_pieces = sum(1 for value in values if value == "Heavy")
            signature: object = (
                (armor_type_count, heavy_pieces)
                if key == _MAX_HEALTH
                else armor_type_count
            )
            source_signatures.add(signature)
            incumbent = witnesses.get(signature)
            if incumbent is None or weights < incumbent:
                witnesses[signature] = weights

        states = tuple(
            ExtremeArmorResourceWeightState(
                objective_key=key,
                weights=witnesses[signature],
            )
            for signature in sorted(witnesses)
        )
        unresolved: list[str] = []
        retained_signatures = {
            state.max_health_signature if key == _MAX_HEALTH else state.armor_type_count
            for state in states
        }
        if retained_signatures != source_signatures:
            unresolved.append(
                "Resource armor-weight search did not preserve every objective-relevant source signature"
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
