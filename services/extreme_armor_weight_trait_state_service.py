from __future__ import annotations

"""Expose reviewed seven-piece armor weight/static-trait states for Extreme search.

The canonical armor/Mundus joint service already owns the reviewed search reduction
for Light/Medium/Heavy armor and static armor traits.  This adapter turns its
pre-Mundus armor states into a reusable finite-axis contract that higher-level
Extreme search can materialize onto a ``PlayerBuild``.

This does *not* close every armor trait globally.  Infused depends on the glyph
axis, while Sturdy/Well-Fitted/Impenetrable/Training belong to other objectives or
runtime contexts.  Only the existing reviewed static source family is claimed.
"""

from dataclasses import dataclass

from models.build_model import PlayerBuild
from services.extreme_armor_mundus_joint_objective_service import (
    ExtremeArmorMundusJointObjectiveService,
    ExtremeArmorMundusPieceChoice,
)


@dataclass(frozen=True)
class ExtremeArmorWeightTraitState:
    objective_key: str
    pieces: tuple[ExtremeArmorMundusPieceChoice, ...]
    direct_delta: float

    @property
    def light_pieces(self) -> int:
        return sum(1 for piece in self.pieces if piece.weight == "Light")

    @property
    def medium_pieces(self) -> int:
        return sum(1 for piece in self.pieces if piece.weight == "Medium")

    @property
    def heavy_pieces(self) -> int:
        return sum(1 for piece in self.pieces if piece.weight == "Heavy")

    @property
    def divines_count(self) -> int:
        return sum(1 for piece in self.pieces if piece.trait == "Divines")

    @property
    def identity(self) -> tuple[tuple[str, str, str], ...]:
        return tuple((piece.slot, piece.weight, piece.trait) for piece in self.pieces)


@dataclass(frozen=True)
class ExtremeArmorWeightTraitStateCatalog:
    objective_key: str
    states: tuple[ExtremeArmorWeightTraitState, ...]
    reviewed_traits: tuple[str, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def reviewed_source_denominator_proven(self) -> bool:
        return bool(self.states) and not self.unresolved


class ExtremeArmorWeightTraitStateService:
    """Adapt the established armor DP into reusable pre-Mundus build states."""

    REVIEWED_OBJECTIVES = ExtremeArmorMundusJointObjectiveService.REVIEWED_OBJECTIVES
    REVIEWED_TRAITS = ("None", "Divines", "Reinforced", "Nirnhoned", "Invigorating")

    @classmethod
    def build(cls, objective_key: str) -> ExtremeArmorWeightTraitStateCatalog:
        key = str(objective_key or "").strip().casefold()
        if key not in cls.REVIEWED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme armor weight/trait objective: {objective_key!r}")

        raw_states = ExtremeArmorMundusJointObjectiveService._states_after_armor(key)
        states = tuple(
            sorted(
                (
                    ExtremeArmorWeightTraitState(
                        objective_key=key,
                        pieces=tuple(state.pieces),
                        direct_delta=float(state.armor_direct_delta),
                    )
                    for state in raw_states
                ),
                key=lambda row: row.identity,
            )
        )
        unresolved = () if states else (
            f"No reviewed armor weight/static-trait states were produced for {key}",
        )
        return ExtremeArmorWeightTraitStateCatalog(
            objective_key=key,
            states=states,
            reviewed_traits=cls.REVIEWED_TRAITS,
            unresolved=unresolved,
        )

    @staticmethod
    def materialize(
        build: PlayerBuild,
        state: ExtremeArmorWeightTraitState,
    ) -> PlayerBuild:
        candidate = PlayerBuild.from_dict(build.to_dict())
        seen: set[str] = set()
        for piece in state.pieces:
            slot = str(piece.slot or "").strip()
            if slot not in candidate.Armor:
                raise ValueError(f"unknown Extreme armor state slot: {slot!r}")
            if slot in seen:
                raise ValueError(f"duplicate Extreme armor state slot: {slot!r}")
            seen.add(slot)
            target = candidate.Armor[slot]
            target["Weight"] = str(piece.weight or "").strip()
            target["Trait"] = "" if piece.trait == "None" else str(piece.trait or "").strip()
            target["Quality"] = "Gold"

        if seen != set(candidate.Armor):
            missing = ", ".join(sorted(set(candidate.Armor) - seen))
            raise ValueError(f"Extreme armor state does not cover all armor slots: {missing}")
        return candidate
