from __future__ import annotations

from dataclasses import dataclass

from services.rotation_healer_channel_runtime_service import (
    RotationHealerChannelMagnitudePolicy,
    RotationHealerChannelRuntimeEvidence,
)
from services.rotation_skill_timing_evidence_service import RotationSkillTimingEvidence


@dataclass(frozen=True)
class RotationHealerReviewedChannelObservation:
    """Human-reviewed channel-heal cadence evidence, excluding channel duration.

    Canonical channel duration belongs to RotationSkillTimingEvidence. Keeping it out
    of this observation prevents reviewed cadence metadata from silently overriding
    imported ESO channel-time evidence.
    """

    source_name: str
    coefficient_number: int
    tick_interval_seconds: float
    first_tick_offset_seconds: float
    tick_on_channel_end_boundary: bool
    magnitude_policy: RotationHealerChannelMagnitudePolicy | None = None
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        name = str(self.source_name or "").strip()
        if not name:
            raise ValueError("reviewed channel observation requires source_name")
        object.__setattr__(self, "source_name", name)
        object.__setattr__(self, "coefficient_number", int(self.coefficient_number))
        if float(self.tick_interval_seconds) <= 0:
            raise ValueError("reviewed channel tick interval must be positive")
        if float(self.first_tick_offset_seconds) < 0:
            raise ValueError("reviewed channel first tick offset must be non-negative")
        object.__setattr__(self, "tick_interval_seconds", float(self.tick_interval_seconds))
        object.__setattr__(
            self,
            "first_tick_offset_seconds",
            float(self.first_tick_offset_seconds),
        )
        if self.magnitude_policy is not None and not isinstance(
            self.magnitude_policy,
            RotationHealerChannelMagnitudePolicy,
        ):
            object.__setattr__(
                self,
                "magnitude_policy",
                RotationHealerChannelMagnitudePolicy(str(self.magnitude_policy)),
            )
        object.__setattr__(
            self,
            "provenance",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.provenance
                    if str(item).strip()
                )
            ),
        )


@dataclass(frozen=True)
class RotationHealerChannelRuntimeEvidenceResolution:
    runtime_evidence: RotationHealerChannelRuntimeEvidence | None
    unresolved: tuple[str, ...] = ()


class RotationHealerChannelRuntimeEvidenceService:
    """Join canonical ESO channel duration to separately reviewed heal-tick cadence."""

    def resolve(
        self,
        *,
        timing: RotationSkillTimingEvidence,
        observation: RotationHealerReviewedChannelObservation | None,
        source_name: str,
        coefficient_number: int,
    ) -> RotationHealerChannelRuntimeEvidenceResolution:
        name = str(source_name or "").strip()
        number = int(coefficient_number)
        unresolved: list[str] = []

        if not timing.is_channeled:
            unresolved.append(
                f"{name} coefficient {number}: canonical skill timing is not channeled"
            )
        duration = timing.channel_time_seconds
        if duration is None or float(duration) <= 0:
            unresolved.append(
                f"{name} coefficient {number}: canonical channel duration is unavailable"
            )
        if observation is None:
            unresolved.append(
                f"{name} coefficient {number}: reviewed channel-heal cadence evidence unavailable"
            )
        elif (
            observation.source_name.casefold() != name.casefold()
            or int(observation.coefficient_number) != number
        ):
            unresolved.append(
                f"{name} coefficient {number}: reviewed channel observation identity mismatch"
            )

        if unresolved or observation is None or duration is None:
            return RotationHealerChannelRuntimeEvidenceResolution(
                runtime_evidence=None,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        evidence = RotationHealerChannelRuntimeEvidence(
            source_name=name,
            coefficient_number=number,
            channel_duration_seconds=float(duration),
            tick_interval_seconds=float(observation.tick_interval_seconds),
            first_tick_offset_seconds=float(observation.first_tick_offset_seconds),
            tick_on_channel_end_boundary=bool(
                observation.tick_on_channel_end_boundary
            ),
            magnitude_policy=observation.magnitude_policy,
            provenance=tuple(
                dict.fromkeys(
                    (
                        timing.source,
                        *observation.provenance,
                    )
                )
            ),
        )
        return RotationHealerChannelRuntimeEvidenceResolution(
            runtime_evidence=evidence,
        )


__all__ = [
    "RotationHealerChannelRuntimeEvidenceResolution",
    "RotationHealerChannelRuntimeEvidenceService",
    "RotationHealerReviewedChannelObservation",
]
