from __future__ import annotations

"""Finite joint Mundus/provisioning dominance for one sustained-DPS action.

The caller supplies the canonical finite choice sets and an exact action consequence
resolver. This service exhausts the full Cartesian product for those two axes while
holding every other build/runtime dimension fixed. If every combination resolves,
the largest exact action total is a proof-safe absolute ceiling for these axes only.
"""

from dataclasses import dataclass
from typing import Protocol

from models.build_model import PlayerBuild
from services.extreme_sustained_dps_action_upper_bound_service import (
    ExtremeSustainedDPSActionDominanceProof,
)
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageOccurrenceEvidence,
)


class ExtremeSustainedDPSFiniteActionEvaluator(Protocol):
    def evaluate(self, build: PlayerBuild) -> RotationActionDamageOccurrenceEvidence: ...


@dataclass(frozen=True)
class ExtremeSustainedDPSMundusProvisioningDominanceResult:
    candidate_key: str
    expected_combinations: int
    evaluated_combinations: int
    resolved_combinations: int
    winning_mundus: str | None
    winning_food: str | None
    upper_bound_damage: float | None
    dominance: ExtremeSustainedDPSActionDominanceProof
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSMundusProvisioningDominanceService:
    """Exhaust one canonical Mundus × mapped provisioning action-damage grid."""

    AXES = ("Mundus", "mapped food/drink")

    @classmethod
    def evaluate(
        cls,
        *,
        candidate_key: str,
        baseline_build: PlayerBuild,
        mundus_choices: tuple[str, ...],
        food_choices: tuple[str, ...],
        evaluator: ExtremeSustainedDPSFiniteActionEvaluator,
        source: str = "canonical Mundus × mapped provisioning finite action search",
    ) -> ExtremeSustainedDPSMundusProvisioningDominanceResult:
        key = str(candidate_key or "").strip()
        if not key:
            raise ValueError("finite action dominance candidate_key is required")

        mundus = cls._choices(mundus_choices, "Mundus")
        foods = cls._choices(food_choices, "food/drink")
        expected = len(mundus) * len(foods)

        unresolved: list[str] = []
        evaluated = 0
        resolved = 0
        winner_damage: float | None = None
        winner_pair: tuple[str, str] | None = None
        coordinate: tuple[float, int] | None = None

        for mundus_name in mundus:
            for food_name in foods:
                build = PlayerBuild.from_dict(baseline_build.to_dict())
                build.Mundus = mundus_name
                build.Food = food_name
                result = evaluator.evaluate(build)
                evaluated += 1

                current_coordinate = (
                    float(result.action_time_seconds),
                    int(result.action_sequence),
                )
                if coordinate is None:
                    coordinate = current_coordinate
                elif coordinate != current_coordinate:
                    unresolved.append(
                        f"{mundus_name} + {food_name}: action coordinate drifted from "
                        f"{coordinate[0]:g}s/{coordinate[1]} to "
                        f"{current_coordinate[0]:g}s/{current_coordinate[1]}"
                    )
                    continue

                if result.unresolved:
                    unresolved.extend(
                        f"{mundus_name} + {food_name}: {item}"
                        for item in result.unresolved
                    )
                    continue

                total = sum(float(item.damage_value) for item in result.occurrences)
                resolved += 1
                pair = (mundus_name, food_name)
                if (
                    winner_damage is None
                    or total > winner_damage + 1e-9
                    or (
                        abs(total - winner_damage) <= 1e-9
                        and tuple(x.casefold() for x in pair)
                        < tuple(x.casefold() for x in winner_pair or pair)
                    )
                ):
                    winner_damage = total
                    winner_pair = pair

        complete = (
            expected > 0
            and evaluated == expected
            and resolved == expected
            and not unresolved
            and winner_damage is not None
        )
        dominance = ExtremeSustainedDPSActionDominanceProof(
            candidate_key=key,
            dominated_axes=cls.AXES if complete else (),
            required_axes=cls.AXES,
            optimistic_upper_damage=winner_damage if complete else None,
            source=source,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

        evidence = (
            f"Canonical Mundus choices searched: {len(mundus)}",
            f"Mapped provisioning choices searched: {len(foods)}",
            f"Joint combinations expected/evaluated/resolved: {expected}/{evaluated}/{resolved}",
            (
                f"Finite-axis action ceiling: {winner_damage:g}"
                if complete and winner_damage is not None
                else "Finite-axis action ceiling withheld because the joint denominator is incomplete"
            ),
            "All non-Mundus/non-provisioning build and runtime dimensions are held fixed",
        )
        return ExtremeSustainedDPSMundusProvisioningDominanceResult(
            candidate_key=key,
            expected_combinations=expected,
            evaluated_combinations=evaluated,
            resolved_combinations=resolved,
            winning_mundus=winner_pair[0] if winner_pair else None,
            winning_food=winner_pair[1] if winner_pair else None,
            upper_bound_damage=winner_damage if complete else None,
            dominance=dominance,
            evidence=evidence,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def _choices(values: tuple[str, ...], label: str) -> tuple[str, ...]:
        cleaned = tuple(
            sorted(
                {
                    str(value or "").strip()
                    for value in values
                    if str(value or "").strip()
                },
                key=str.casefold,
            )
        )
        if not cleaned:
            raise ValueError(f"finite action dominance requires at least one {label} choice")
        return cleaned


__all__ = [
    "ExtremeSustainedDPSFiniteActionEvaluator",
    "ExtremeSustainedDPSMundusProvisioningDominanceResult",
    "ExtremeSustainedDPSMundusProvisioningDominanceService",
]
