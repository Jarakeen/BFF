from __future__ import annotations

"""Role-specific interpretation of shared runtime effect windows for healer review.

This service owns no aura lifetime mechanics.  It consumes canonical
``RuntimeEffectActiveWindow`` instances plus reviewed encounter windows and asks a
narrow coaching question: was a reviewed healer effect already active when the
mechanic began?
"""

from dataclasses import dataclass
from typing import Iterable

from minmax.runtime_effect_window import RuntimeEffectActiveWindow, partition_runtime_effect_windows
from services.performance_raid_review_mechanic_window_service import RaidReviewEncounterWindow


@dataclass(frozen=True, slots=True)
class RaidReviewHealerEffectRequirement:
    semantic_key: str
    label: str
    effect_names: tuple[str, ...]
    mechanic_keys: tuple[str, ...]
    source_actor_id: int | None = None
    minimum_active_targets: int = 1
    reviewed: bool = True

    def __post_init__(self) -> None:
        if self.reviewed and not str(self.semantic_key or "").strip():
            raise ValueError("Reviewed healer coverage requirements require semantic_key.")
        if self.reviewed and not tuple(name for name in self.effect_names if str(name).strip()):
            raise ValueError("Reviewed healer coverage requirements require effect_names.")
        if self.reviewed and not tuple(key for key in self.mechanic_keys if str(key).strip()):
            raise ValueError("Reviewed healer coverage requirements require mechanic_keys.")
        if int(self.minimum_active_targets) < 1:
            raise ValueError("minimum_active_targets must be at least 1")


@dataclass(frozen=True, slots=True)
class RaidReviewHealerEffectCoverageObservation:
    report_code: str
    fight_id: int
    mechanic_semantic_key: str
    mechanic_label: str
    mechanic_start_seconds: float
    requirement_semantic_key: str
    requirement_label: str
    source_actor_id: int | None
    covered: bool
    active_target_count: int
    active_effect_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RaidReviewHealerEffectCoverageResult:
    observations: tuple[RaidReviewHealerEffectCoverageObservation, ...]
    unresolved: tuple[str, ...] = ()


class PerformanceRaidReviewHealerEffectCoverageService:
    """Evaluate reviewed healer effects at reviewed mechanic start boundaries."""

    def evaluate(
        self,
        *,
        effect_windows: Iterable[RuntimeEffectActiveWindow],
        mechanic_windows: Iterable[RaidReviewEncounterWindow],
        requirements: Iterable[RaidReviewHealerEffectRequirement],
    ) -> RaidReviewHealerEffectCoverageResult:
        runtime_windows = tuple(effect_windows)
        mechanics = tuple(window for window in mechanic_windows if window.reviewed)
        reviewed_requirements = tuple(item for item in requirements if item.reviewed)
        observations: list[RaidReviewHealerEffectCoverageObservation] = []
        unresolved: list[str] = []

        mechanics_by_key = {window.semantic_key: window for window in mechanics}

        for requirement in reviewed_requirements:
            matching_mechanics = [
                mechanics_by_key[key]
                for key in requirement.mechanic_keys
                if key in mechanics_by_key
            ]
            missing = [key for key in requirement.mechanic_keys if key not in mechanics_by_key]
            for key in missing:
                unresolved.append(
                    f"{requirement.label}: reviewed mechanic window {key} was not available for coverage evaluation."
                )

            wanted_names = {str(name).strip().casefold() for name in requirement.effect_names if str(name).strip()}
            wanted_source = (
                None
                if requirement.source_actor_id is None
                else f"esologs:actor:{int(requirement.source_actor_id)}"
            )

            for mechanic in matching_mechanics:
                active = partition_runtime_effect_windows(
                    runtime_windows,
                    at_time_seconds=float(mechanic.start_seconds),
                ).active
                matching = tuple(
                    window
                    for window in active
                    if window.effect_name.casefold() in wanted_names
                    and (wanted_source is None or window.source == wanted_source)
                )
                targets = {window.target for window in matching if window.target is not None}
                # Untargeted effects still count as one observed active coverage surface.
                active_target_count = len(targets) if targets else (1 if matching else 0)
                observations.append(
                    RaidReviewHealerEffectCoverageObservation(
                        report_code=mechanic.report_code,
                        fight_id=int(mechanic.fight_id),
                        mechanic_semantic_key=mechanic.semantic_key,
                        mechanic_label=mechanic.label,
                        mechanic_start_seconds=float(mechanic.start_seconds),
                        requirement_semantic_key=requirement.semantic_key,
                        requirement_label=requirement.label,
                        source_actor_id=(
                            None
                            if requirement.source_actor_id is None
                            else int(requirement.source_actor_id)
                        ),
                        covered=active_target_count >= int(requirement.minimum_active_targets),
                        active_target_count=active_target_count,
                        active_effect_names=tuple(sorted({window.effect_name for window in matching})),
                    )
                )

        observations.sort(
            key=lambda row: (
                row.report_code,
                row.fight_id,
                row.mechanic_start_seconds,
                row.requirement_semantic_key,
            )
        )
        return RaidReviewHealerEffectCoverageResult(
            observations=tuple(observations),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "PerformanceRaidReviewHealerEffectCoverageService",
    "RaidReviewHealerEffectCoverageObservation",
    "RaidReviewHealerEffectCoverageResult",
    "RaidReviewHealerEffectRequirement",
]
