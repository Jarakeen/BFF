from __future__ import annotations

"""Project scheduled potion uses into canonical Phase 4 restoration events."""

from pathlib import Path
import math

from engine.config import get_data_dir
from minmax.potion_use_event import PotionUseEventResolver
from minmax.resource_costs import ResourceType
from minmax.restoration_events import ResourceRestorationEvent
from minmax.rotation_plan import RotationActionKind
from models.build_model import PlayerBuild
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateRestorationEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


_RESOURCE_BY_TRAIT = {
    "restore magicka": ResourceType.MAGICKA,
    "restore stamina": ResourceType.STAMINA,
    "restore health": ResourceType.HEALTH,
}


class RotationCandidatePotionRestorationEvidenceService:
    """Convert exact scheduled potion actions into sourced restoration events."""

    def __init__(
        self,
        *,
        build: PlayerBuild,
        database_path: str | Path | None = None,
        event_resolver: PotionUseEventResolver | None = None,
    ) -> None:
        self.build = build
        database = (
            Path(database_path)
            if database_path is not None
            else get_data_dir() / "eso.db"
        )
        self.event_resolver = event_resolver or PotionUseEventResolver(
            database_path=database
        )

    @staticmethod
    def _normalized(value: object) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _resource_for_trait(cls, trait: str) -> ResourceType | None:
        return _RESOURCE_BY_TRAIT.get(cls._normalized(trait).casefold())

    @staticmethod
    def _integral_amount(value: float | None) -> int | None:
        if value is None:
            return None
        number = float(value)
        if not math.isfinite(number) or number < 0.0:
            return None
        rounded = round(number)
        if abs(number - rounded) > 1e-9:
            return None
        return int(rounded)

    def evaluate_plan(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> RotationCandidateRestorationEvidence:
        potion_name = self._normalized(getattr(self.build, "Potion", ""))
        potion_actions = tuple(
            action
            for action in candidate.plan.actions
            if action.kind is RotationActionKind.POTION
        )

        if not potion_actions:
            return RotationCandidateRestorationEvidence(
                candidate_id=candidate.candidate_id,
            )

        unresolved: list[str] = []
        if not potion_name:
            unresolved.append(
                "scheduled potion restoration requires a saved potion selection"
            )
            return RotationCandidateRestorationEvidence(
                candidate_id=candidate.candidate_id,
                unresolved=tuple(unresolved),
            )

        for action in potion_actions:
            action_name = self._normalized(action.name)
            if action_name.casefold() != potion_name.casefold():
                unresolved.append(
                    f"scheduled potion identity {action_name!r} does not match saved potion {potion_name!r}"
                )

        event = self.event_resolver.resolve(potion_name)
        unresolved.extend(tuple(event.unresolved))
        if not event.resolved:
            if not event.unresolved:
                unresolved.append(
                    f"scheduled potion restoration could not resolve source evidence for {potion_name!r}"
                )
            return RotationCandidateRestorationEvidence(
                candidate_id=candidate.candidate_id,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        restore_rows: list[tuple[ResourceType, int, str]] = []
        for trait in event.instant_restores:
            resource = self._resource_for_trait(trait.trait)
            if resource is None:
                unresolved.append(
                    f"unsupported instant potion restoration trait: {trait.trait}"
                )
                continue
            amount = self._integral_amount(trait.magnitude)
            if amount is None:
                unresolved.append(
                    f"instant potion restoration magnitude is not a resolved non-negative integer for {trait.trait}"
                )
                continue
            restore_rows.append(
                (
                    resource,
                    amount,
                    f"{potion_name}: {trait.trait}",
                )
            )

        if not restore_rows:
            unresolved.append(
                "resolved potion supplies no canonical instant resource restoration rows"
            )

        events = tuple(
            ResourceRestorationEvent(
                time_seconds=float(action.time_seconds),
                resource=resource,
                amount=amount,
                source=source,
            )
            for action in potion_actions
            for resource, amount, source in restore_rows
        )

        return RotationCandidateRestorationEvidence(
            candidate_id=candidate.candidate_id,
            restoration_events=events,
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = [
    "RotationCandidatePotionRestorationEvidenceService",
]
