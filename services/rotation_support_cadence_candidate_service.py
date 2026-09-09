from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol

from minmax.refresh_cadence_duration_scheduler import RotationRefreshIntervalPolicy
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_duration_refinement_service import RotationDurationRefinement
from services.rotation_local_cadence_duration_refinement_service import (
    RotationLocalCadenceDurationRefinementService,
)
from services.rotation_support_refresh_cadence_service import (
    RotationSupportRefreshCadenceCandidate,
    RotationSupportRefreshCadenceResult,
)


def _canonical_skill_id(value: object) -> str:
    text = str(value or "").strip().casefold().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


class _DurationRefiner(Protocol):
    def refine(
        self,
        plan: RotationPlan,
        *,
        priorities: AbilityPriorityList | None = None,
        refresh_cadences: tuple[RotationRefreshIntervalPolicy, ...] = (),
    ) -> RotationDurationRefinement: ...


@dataclass(frozen=True)
class RotationSupportCadencePlanCandidate:
    """One complete refined rotation produced from a support cadence proposal."""

    candidate_id: str
    effect_key: str
    source_skill_id: str
    cadence: RotationSupportRefreshCadenceCandidate
    refresh_policy: RotationRefreshIntervalPolicy
    refinement: RotationDurationRefinement

    @property
    def plan(self) -> RotationPlan:
        return self.refinement.plan


class RotationSupportCadenceCandidateService:
    """Materialize one support-effect cadence family as complete rotation plans.

    This is intentionally a local expansion step: one cadence result varies one
    support skill across its proposed intervals. It does not form Cartesian products
    across multiple effects, rank candidates, or absorb sustain/workload/effect
    evaluation. Each resulting plan can flow through those existing Phase 13 layers.

    The cadence proposal uses semantic ``lower_snake_case`` skill identity. The
    seed plan may use a display name, so this service resolves the matching skill
    action and then builds the scheduler policy with that exact plan name/bar.

    The default duration refiner is deliberately local: previously accepted cadence
    scheduling for unrelated duration skills is preserved unless the newly proposed
    cadence actually collides with and displaces one of those timeline slots.
    """

    def __init__(self, duration_refiner: _DurationRefiner | None = None) -> None:
        self.duration_refiner = (
            duration_refiner or RotationLocalCadenceDurationRefinementService()
        )

    def materialize(
        self,
        *,
        seed_plan: RotationPlan,
        cadence_result: RotationSupportRefreshCadenceResult,
        priorities: AbilityPriorityList | None = None,
        source_bar: str | None = None,
    ) -> tuple[RotationSupportCadencePlanCandidate, ...]:
        if not cadence_result.candidates:
            return ()

        normalized_bar = self._normalize_bar(source_bar)
        source_action = self._resolve_source_action(
            seed_plan=seed_plan,
            source_skill_id=cadence_result.source_skill_id,
            source_bar=normalized_bar,
        )

        materialized: list[RotationSupportCadencePlanCandidate] = []
        for cadence in cadence_result.candidates:
            if cadence.effect_key != cadence_result.effect_key:
                raise ValueError("cadence candidate effect_key does not match its result")
            if cadence.source_skill_id != cadence_result.source_skill_id:
                raise ValueError("cadence candidate source_skill_id does not match its result")

            refresh_policy = RotationRefreshIntervalPolicy(
                skill_name=source_action.name or cadence_result.source_skill_id,
                interval_seconds=cadence.recast_interval_seconds,
                bar=source_action.bar,
                source=(
                    f"support cadence candidate {cadence_result.effect_key}:"
                    f"{cadence.candidate_key}"
                ),
            )
            refinement = self.duration_refiner.refine(
                seed_plan,
                priorities=priorities,
                refresh_cadences=(refresh_policy,),
            )
            materialized.append(
                RotationSupportCadencePlanCandidate(
                    candidate_id=self._candidate_id(cadence, source_action.bar),
                    effect_key=cadence_result.effect_key,
                    source_skill_id=cadence_result.source_skill_id,
                    cadence=cadence,
                    refresh_policy=refresh_policy,
                    refinement=refinement,
                )
            )

        return tuple(materialized)

    @staticmethod
    def _normalize_bar(source_bar: str | None) -> str | None:
        if source_bar is None:
            return None
        bar = str(source_bar).strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("source_bar must be 'front' or 'back'")
        return bar

    @classmethod
    def _resolve_source_action(
        cls,
        *,
        seed_plan: RotationPlan,
        source_skill_id: str,
        source_bar: str | None,
    ) -> RotationAction:
        skill_id = _canonical_skill_id(source_skill_id)
        if not skill_id:
            raise ValueError("cadence result source_skill_id is required")

        matches: dict[tuple[str, str | None], RotationAction] = {}
        for action in seed_plan.actions:
            if action.kind is not RotationActionKind.SKILL or not action.name:
                continue
            if _canonical_skill_id(action.name) != skill_id:
                continue
            if source_bar is not None and action.bar != source_bar:
                continue
            matches[(action.name.casefold(), action.bar)] = action

        if not matches:
            scope = f" on {source_bar} bar" if source_bar else ""
            raise ValueError(
                f"support cadence source skill {source_skill_id!r}{scope} is not present in the seed plan"
            )
        if len(matches) > 1:
            bars = ", ".join(sorted(action.bar or "unspecified" for action in matches.values()))
            raise ValueError(
                f"support cadence source skill {source_skill_id!r} is ambiguous across seed-plan bars "
                f"({bars}); source_bar is required"
            )
        return next(iter(matches.values()))

    @staticmethod
    def _candidate_id(
        cadence: RotationSupportRefreshCadenceCandidate, source_bar: str | None,
    ) -> str:
        return ":".join(
            (
                cadence.effect_key,
                cadence.source_skill_id,
                cadence.candidate_key,
                source_bar or "unspecified",
            )
        )


__all__ = [
    "RotationSupportCadenceCandidateService",
    "RotationSupportCadencePlanCandidate",
]
