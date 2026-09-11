from __future__ import annotations

"""Project saved-build gear rules onto rotation bar legality.

Oakensoul Ring does not remove the character's backup weapon equipment, but while
it is equipped the backup weapon set cannot become active. This service derives
that restriction from the same canonical equipped-set counting used by gear math
and decorates an existing RotationActiveBarAssessment without changing generic
rotation bar semantics for ordinary builds.
"""

from dataclasses import replace

from minmax.gear_stat_inputs import GearStatInputResolver
from minmax.rotation_active_bar_legality import (
    RotationActiveBarAssessment,
    RotationActiveBarViolation,
)
from minmax.rotation_plan import RotationActionKind, RotationPlan
from models.build_model import PlayerBuild


OAKENSOUL_RING = "Oakensoul Ring"


class RotationSavedBuildBarAccessService:
    """Apply reviewed saved-build bar-access restrictions to one final plan."""

    @staticmethod
    def _oakensoul_count(build: PlayerBuild, *, active_bar: str) -> int:
        counts = GearStatInputResolver.equipped_set_counts(build, active_bar=active_bar)
        return int(counts.get(OAKENSOUL_RING, 0))

    @classmethod
    def restrict(
        cls,
        build: PlayerBuild,
        plan: RotationPlan,
        assessment: RotationActiveBarAssessment,
    ) -> RotationActiveBarAssessment:
        front_count = cls._oakensoul_count(build, active_bar="front")
        back_count = cls._oakensoul_count(build, active_bar="back")

        # Oakensoul is jewelry and therefore shared by both bar snapshots. A
        # disagreement means the saved-build evidence is malformed; fail closed.
        if bool(front_count) != bool(back_count):
            violation = RotationActiveBarViolation(
                time_seconds=0.0,
                action_name="Oakensoul Ring",
                action_kind=RotationActionKind.BAR_SWAP,
                scheduled_bar=None,
                active_bar=assessment.initial_bar,
                reason="saved build disagrees on shared Oakensoul Ring equipment across weapon bars",
            )
            return replace(
                assessment,
                violations=assessment.violations + (violation,),
            )

        if front_count <= 0:
            return assessment

        violations = list(assessment.violations)
        if assessment.initial_bar != "front":
            violations.append(
                RotationActiveBarViolation(
                    time_seconds=0.0,
                    action_name="Oakensoul Ring",
                    action_kind=RotationActionKind.BAR_SWAP,
                    scheduled_bar=assessment.initial_bar,
                    active_bar=assessment.initial_bar,
                    reason="Oakensoul Ring permits only the primary/front weapon set to be active",
                )
            )

        for action in plan.actions:
            if action.kind is not RotationActionKind.BAR_SWAP:
                continue
            violations.append(
                RotationActiveBarViolation(
                    time_seconds=float(action.time_seconds),
                    action_name=str(action.name or "Bar Swap"),
                    action_kind=action.kind,
                    scheduled_bar=action.bar,
                    active_bar="front",
                    reason="Oakensoul Ring prevents swapping to the backup weapon set",
                )
            )

        return RotationActiveBarAssessment(
            initial_bar=assessment.initial_bar,
            final_bar="front" if assessment.initial_bar == "front" else assessment.final_bar,
            violations=tuple(violations),
        )


__all__ = ["RotationSavedBuildBarAccessService"]
