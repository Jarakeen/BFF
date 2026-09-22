from __future__ import annotations

"""Finite generated Mundus + food axes for exact sustained-DPS witnesses."""

from dataclasses import dataclass, replace

from models.build_model import PlayerBuild
from services.extreme_sustained_dps_axis_dominance_composition_service import (
    ExtremeSustainedDPSAxisCoverageProof,
)
from services.extreme_sustained_dps_cross_axis_context_service import (
    ExtremeSustainedDPSCrossAxisContext,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSIndexedFrontierAxis,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedMundusFoodAxisState:
    context: ExtremeSustainedDPSCrossAxisContext
    mundus: str | None = None
    food: str | None = None

    @property
    def complete(self) -> bool:
        return bool(self.mundus and self.food)


class ExtremeSustainedDPSGeneratedMundusFoodAxisAdapterService:
    """Mutate exact build state across one proven finite Mundus/food denominator."""

    def __init__(
        self,
        *,
        mundus_choices: tuple[str, ...],
        food_choices: tuple[str, ...],
        denominator_proven: bool,
        unresolved: tuple[str, ...] = (),
    ) -> None:
        self.mundus_choices = self._choices(mundus_choices)
        self.food_choices = self._choices(food_choices)
        self.unresolved = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in unresolved
                if str(item).strip()
            )
        )
        self.denominator_proven = bool(
            denominator_proven
            and self.mundus_choices
            and self.food_choices
            and not self.unresolved
        )

    @staticmethod
    def _choices(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    str(value or "").strip()
                    for value in values
                    if str(value or "").strip()
                },
                key=str.casefold,
            )
        )

    def _require_denominator(self) -> None:
        if not self.denominator_proven:
            detail = "; ".join(self.unresolved)
            raise ValueError(
                "generated Mundus/food axis requires a proven finite denominator"
                + (f": {detail}" if detail else "")
            )

    @staticmethod
    def _with_build(
        context: ExtremeSustainedDPSCrossAxisContext,
        build: PlayerBuild,
    ) -> ExtremeSustainedDPSCrossAxisContext:
        return replace(context, build=build)

    def _mundus_count(self, _state: object) -> int:
        self._require_denominator()
        return len(self.mundus_choices)

    def _mundus_at(
        self,
        state: ExtremeSustainedDPSGeneratedMundusFoodAxisState,
        index: int,
    ) -> ExtremeSustainedDPSGeneratedMundusFoodAxisState:
        self._require_denominator()
        target = int(index)
        if target < 0 or target >= len(self.mundus_choices):
            raise IndexError("generated Mundus choice index out of range")
        build = PlayerBuild.from_dict(state.context.build.to_dict())
        selected = self.mundus_choices[target]
        build.Mundus = selected
        return replace(
            state,
            mundus=selected,
            food=None,
            context=self._with_build(state.context, build),
        )

    def _food_count(
        self,
        state: ExtremeSustainedDPSGeneratedMundusFoodAxisState,
    ) -> int:
        self._require_denominator()
        if not state.mundus:
            raise ValueError(
                "generated food axis requires a selected Mundus first"
            )
        return len(self.food_choices)

    def _food_at(
        self,
        state: ExtremeSustainedDPSGeneratedMundusFoodAxisState,
        index: int,
    ) -> ExtremeSustainedDPSGeneratedMundusFoodAxisState:
        self._require_denominator()
        if not state.mundus:
            raise ValueError(
                "generated food axis requires a selected Mundus first"
            )
        target = int(index)
        if target < 0 or target >= len(self.food_choices):
            raise IndexError("generated food choice index out of range")
        build = PlayerBuild.from_dict(state.context.build.to_dict())
        selected = self.food_choices[target]
        build.Food = selected
        return replace(
            state,
            food=selected,
            context=self._with_build(state.context, build),
        )

    def root(
        self,
        context: ExtremeSustainedDPSCrossAxisContext,
    ) -> ExtremeSustainedDPSGeneratedMundusFoodAxisState:
        return ExtremeSustainedDPSGeneratedMundusFoodAxisState(
            context=context
        )

    def coverage(self) -> ExtremeSustainedDPSAxisCoverageProof:
        unresolved = self.unresolved
        if not self.denominator_proven and not unresolved:
            unresolved = (
                "Generated Mundus/food denominator is not proven complete",
            )
        return ExtremeSustainedDPSAxisCoverageProof(
            source="generated exact-witness Mundus + food denominator",
            dominated_axes=(
                ("mundus", "food")
                if self.denominator_proven
                else ()
            ),
            unresolved=tuple(unresolved),
        )

    def axes(self) -> tuple[ExtremeSustainedDPSIndexedFrontierAxis, ...]:
        return (
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Mundus",
                candidate_count=self._mundus_count,
                candidate_at=self._mundus_at,
            ),
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Food",
                candidate_count=self._food_count,
                candidate_at=self._food_at,
            ),
        )


__all__ = [
    "ExtremeSustainedDPSGeneratedMundusFoodAxisAdapterService",
    "ExtremeSustainedDPSGeneratedMundusFoodAxisState",
]
