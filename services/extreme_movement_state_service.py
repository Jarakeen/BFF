from __future__ import annotations

from dataclasses import dataclass

from minmax.formulas.final_calculations import (
    calculate_run_speed,
    calculate_sneak_speed,
    calculate_sprint_speed,
)


@dataclass(frozen=True)
class ExtremeMovementStateInputs:
    """Canonical movement-source channels shared by Extreme movement records."""

    base_walk_speed: float = 3.0
    buff_movement_speed: float = 0.0
    skill_movement_speed: float = 0.0
    item_movement_speed: float = 0.0
    set_movement_speed: float = 0.0
    mundus_movement_speed: float = 0.0
    cp_movement_speed: float = 0.0

    set_sprint_speed: float = 0.0
    buff_sprint_speed: float = 0.0
    skill_sprint_speed: float = 0.0
    cp_sprint_speed: float = 0.0

    skill_normal_sneak_speed: float = 0.0
    cp_sneak_speed: float = 0.0
    skill_sneak_speed: float = 0.0
    skill2_sneak_speed: float = 0.0


@dataclass(frozen=True)
class ExtremeMovementStateResult:
    objective_key: str
    raw_speed: float
    effective_speed: float
    base_walk_speed: float
    effective_cap_multiplier: float = 2.0

    @property
    def raw_multiplier(self) -> float:
        if self.base_walk_speed <= 0:
            return 0.0
        return self.raw_speed / self.base_walk_speed

    @property
    def effective_multiplier(self) -> float:
        if self.base_walk_speed <= 0:
            return 0.0
        return self.effective_speed / self.base_walk_speed


class ExtremeMovementStateService:
    """Project all three Extreme movement records from one canonical formula set.

    The UESP movement equations remain owned by ``final_calculations``.  Extreme
    only supplies a common source-channel contract and reports the raw formula
    result beside the reviewed 200% unmounted effective-speed ceiling.  Candidate
    discovery for skills, sets, CP, Mundus, and item sources remains a separate
    search problem and is deliberately not duplicated here.
    """

    EFFECTIVE_CAP_MULTIPLIER = 2.0

    @classmethod
    def evaluate(cls, objective_key: str, inputs: ExtremeMovementStateInputs) -> ExtremeMovementStateResult:
        key = str(objective_key or "").strip().casefold()
        if float(inputs.base_walk_speed) <= 0:
            raise ValueError("base_walk_speed must be positive")

        common = dict(
            base_walk_speed=float(inputs.base_walk_speed),
            buff_movement_speed=float(inputs.buff_movement_speed),
            skill_movement_speed=float(inputs.skill_movement_speed),
            item_movement_speed=float(inputs.item_movement_speed),
            set_movement_speed=float(inputs.set_movement_speed),
            mundus_movement_speed=float(inputs.mundus_movement_speed),
            cp_movement_speed=float(inputs.cp_movement_speed),
        )

        if key == "movement_speed":
            raw = calculate_run_speed(**common)
        elif key == "sprint_speed":
            raw = calculate_sprint_speed(
                **common,
                set_sprint_speed=float(inputs.set_sprint_speed),
                buff_sprint_speed=float(inputs.buff_sprint_speed),
                skill_sprint_speed=float(inputs.skill_sprint_speed),
                cp_sprint_speed=float(inputs.cp_sprint_speed),
            )
        elif key == "stealthed_movement_speed":
            raw = calculate_sneak_speed(
                **common,
                skill_normal_sneak_speed=float(inputs.skill_normal_sneak_speed),
                cp_sneak_speed=float(inputs.cp_sneak_speed),
                skill_sneak_speed=float(inputs.skill_sneak_speed),
                skill2_sneak_speed=float(inputs.skill2_sneak_speed),
            )
        else:
            raise ValueError(f"Unsupported Extreme movement objective: {objective_key!r}")

        cap = float(inputs.base_walk_speed) * cls.EFFECTIVE_CAP_MULTIPLIER
        return ExtremeMovementStateResult(
            objective_key=key,
            raw_speed=float(raw),
            effective_speed=min(float(raw), cap),
            base_walk_speed=float(inputs.base_walk_speed),
            effective_cap_multiplier=cls.EFFECTIVE_CAP_MULTIPLIER,
        )


__all__ = [
    "ExtremeMovementStateInputs",
    "ExtremeMovementStateResult",
    "ExtremeMovementStateService",
]
