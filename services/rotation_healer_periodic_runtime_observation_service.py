from __future__ import annotations

from dataclasses import dataclass
import math

from services.rotation_healer_periodic_runtime_evidence_service import (
    RotationHealerReviewedRuntimeObservation,
)


@dataclass(frozen=True)
class RotationHealerPeriodicObservedSample:
    """One reviewed activation plus observed heal-event timestamps.

    Timestamps are relative to the same combat-log origin. This object deliberately
    carries no inferred refresh policy. It is suitable for deriving first-tick
    placement and, when the observation extends through canonical expiry, whether
    a tick occurred exactly on that boundary.
    """

    source_name: str
    coefficient_number: int
    activation_time_seconds: float
    observed_tick_times_seconds: tuple[float, ...]
    observation_end_seconds: float
    provenance: tuple[str, ...]
    game_version: str | None = None

    def __post_init__(self) -> None:
        name = str(self.source_name or "").strip()
        if not name:
            raise ValueError("periodic observed sample requires source_name")
        object.__setattr__(self, "source_name", name)
        object.__setattr__(self, "coefficient_number", int(self.coefficient_number))

        activation = float(self.activation_time_seconds)
        end = float(self.observation_end_seconds)
        if not math.isfinite(activation) or activation < 0:
            raise ValueError("activation_time_seconds must be finite and non-negative")
        if not math.isfinite(end) or end < activation:
            raise ValueError("observation_end_seconds must be finite and not precede activation")
        object.__setattr__(self, "activation_time_seconds", activation)
        object.__setattr__(self, "observation_end_seconds", end)

        ticks = tuple(sorted(float(value) for value in self.observed_tick_times_seconds))
        if any(not math.isfinite(value) or value < activation for value in ticks):
            raise ValueError("observed tick timestamps must be finite and not precede activation")
        object.__setattr__(self, "observed_tick_times_seconds", ticks)

        provenance = tuple(
            dict.fromkeys(
                str(item).strip() for item in self.provenance if str(item).strip()
            )
        )
        if not provenance:
            raise ValueError("periodic observed sample requires provenance")
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(
            self,
            "game_version",
            str(self.game_version or "").strip() or None,
        )


@dataclass(frozen=True)
class RotationHealerPeriodicObservedResolution:
    observation: RotationHealerReviewedRuntimeObservation | None
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class RotationHealerPeriodicRuntimeObservationService:
    """Derive only runtime facts directly supported by reviewed event timestamps."""

    def resolve(
        self,
        *,
        sample: RotationHealerPeriodicObservedSample,
        canonical_duration_seconds: float,
        canonical_cadence_seconds: float,
        tolerance_seconds: float = 0.01,
        cadence_tolerance_seconds: float = 0.1,
    ) -> RotationHealerPeriodicObservedResolution:
        duration = float(canonical_duration_seconds)
        cadence = float(canonical_cadence_seconds)
        tolerance = float(tolerance_seconds)
        cadence_tolerance = float(cadence_tolerance_seconds)
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("canonical_duration_seconds must be finite and positive")
        if not math.isfinite(cadence) or cadence <= 0:
            raise ValueError("canonical_cadence_seconds must be finite and positive")
        if not math.isfinite(tolerance) or tolerance < 0:
            raise ValueError("tolerance_seconds must be finite and non-negative")
        if not math.isfinite(cadence_tolerance) or cadence_tolerance < 0:
            raise ValueError(
                "cadence_tolerance_seconds must be finite and non-negative"
            )

        evidence = list(sample.provenance)
        unresolved: list[str] = []
        ticks = sample.observed_tick_times_seconds

        first_offset: float | None = None
        if ticks:
            first_offset = ticks[0] - sample.activation_time_seconds
            evidence.append(
                f"observed first periodic heal at +{first_offset:g}s from activation"
            )
        else:
            unresolved.append(
                f"{sample.source_name} coefficient {sample.coefficient_number}: no periodic heal event was observed"
            )

        expiry = sample.activation_time_seconds + duration
        expiry_rule: bool | None = None
        if sample.observation_end_seconds + tolerance >= expiry:
            expiry_rule = any(abs(value - expiry) <= tolerance for value in ticks)
            evidence.append(
                "observed canonical expiry boundary with "
                + ("a heal event" if expiry_rule else "no heal event")
            )
        else:
            unresolved.append(
                f"{sample.source_name} coefficient {sample.coefficient_number}: observation does not extend through canonical expiry"
            )

        if len(ticks) >= 2:
            intervals = tuple(
                ticks[index + 1] - ticks[index]
                for index in range(len(ticks) - 1)
            )
            if any(
                abs(value - cadence) > cadence_tolerance for value in intervals
            ):
                unresolved.append(
                    f"{sample.source_name} coefficient {sample.coefficient_number}: observed tick spacing conflicts with canonical cadence"
                )
            else:
                evidence.append(
                    f"observed tick spacing agrees with canonical {cadence:g}s cadence"
                )

        if first_offset is None or expiry_rule is None:
            return RotationHealerPeriodicObservedResolution(
                observation=None,
                evidence=tuple(dict.fromkeys(evidence)),
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        observation = RotationHealerReviewedRuntimeObservation(
            source_name=sample.source_name,
            coefficient_number=sample.coefficient_number,
            first_tick_offset_seconds=first_offset,
            tick_on_expiry_boundary=expiry_rule,
            refresh_policy=None,
            provenance=tuple(dict.fromkeys(evidence)),
            game_version=sample.game_version,
        )
        return RotationHealerPeriodicObservedResolution(
            observation=observation,
            evidence=tuple(dict.fromkeys(evidence)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
