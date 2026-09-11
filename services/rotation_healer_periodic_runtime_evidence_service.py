from __future__ import annotations

from dataclasses import dataclass
import math

from services.rotation_healer_canonical_periodic_timing_service import (
    RotationHealerCanonicalPeriodicTimingResolution,
)
from services.rotation_healer_periodic_runtime_service import (
    RotationHealerPeriodicMagnitudePolicy,
    RotationHealerPeriodicRefreshPolicy,
    RotationHealerPeriodicRuntimeEvidence,
)


@dataclass(frozen=True)
class RotationHealerReviewedRuntimeObservation:
    """Reviewed runtime facts that canonical cadence/duration text does not prove.

    This overlay is intentionally narrow. It may supply the concrete first-tick
    placement, expiry-boundary rule, repeated-application refresh behavior, and
    periodic magnitude timing policy, but it does not replace canonical component
    identity, cadence, or duration. Provenance is required so a manually reviewed
    observation cannot silently become an unexplained combat rule.
    """

    source_name: str
    coefficient_number: int
    first_tick_offset_seconds: float | None = None
    tick_on_expiry_boundary: bool | None = None
    refresh_policy: RotationHealerPeriodicRefreshPolicy | None = None
    magnitude_policy: RotationHealerPeriodicMagnitudePolicy | None = None
    provenance: tuple[str, ...] = ()
    game_version: str | None = None

    def __post_init__(self) -> None:
        source_name = str(self.source_name or "").strip()
        if not source_name:
            raise ValueError("reviewed healer runtime observation requires source_name")
        object.__setattr__(self, "source_name", source_name)
        object.__setattr__(self, "coefficient_number", int(self.coefficient_number))

        if self.first_tick_offset_seconds is not None:
            value = float(self.first_tick_offset_seconds)
            if not math.isfinite(value) or value < 0:
                raise ValueError(
                    "first_tick_offset_seconds must be finite and non-negative when present"
                )
            object.__setattr__(self, "first_tick_offset_seconds", value)

        if self.refresh_policy is not None and not isinstance(
            self.refresh_policy, RotationHealerPeriodicRefreshPolicy
        ):
            object.__setattr__(
                self,
                "refresh_policy",
                RotationHealerPeriodicRefreshPolicy(str(self.refresh_policy)),
            )
        if self.magnitude_policy is not None and not isinstance(
            self.magnitude_policy, RotationHealerPeriodicMagnitudePolicy
        ):
            object.__setattr__(
                self,
                "magnitude_policy",
                RotationHealerPeriodicMagnitudePolicy(str(self.magnitude_policy)),
            )

        provenance = tuple(
            dict.fromkeys(
                str(item).strip() for item in self.provenance if str(item).strip()
            )
        )
        object.__setattr__(self, "provenance", provenance)
        if any(
            value is not None
            for value in (
                self.first_tick_offset_seconds,
                self.tick_on_expiry_boundary,
                self.refresh_policy,
                self.magnitude_policy,
            )
        ) and not provenance:
            raise ValueError(
                "reviewed healer runtime facts require provenance"
            )

        version = str(self.game_version or "").strip() or None
        object.__setattr__(self, "game_version", version)


@dataclass(frozen=True)
class RotationHealerPeriodicRuntimeEvidenceResolution:
    source_name: str
    coefficient_number: int
    runtime_evidence: RotationHealerPeriodicRuntimeEvidence | None
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.runtime_evidence is not None and not self.unresolved


class RotationHealerPeriodicRuntimeEvidenceService:
    """Join canonical HoT cadence/duration with reviewed runtime observations.

    Canonical skill text remains authoritative for component identity, cadence,
    and duration. Reviewed observations are allowed to fill only the runtime facts
    that those sources deliberately leave open. Magnitude timing is carried when
    reviewed but is not required for ordinary cast-resolved timing projection; it
    becomes required only when a caller asks for exact-time tick magnitude evaluation.
    If any required timing fact is absent, the service fails closed rather than
    converting a plausible player assumption into authoritative healer coverage.
    """

    def resolve(
        self,
        *,
        canonical: RotationHealerCanonicalPeriodicTimingResolution,
        observation: RotationHealerReviewedRuntimeObservation | None = None,
        repeated_applications: bool = False,
    ) -> RotationHealerPeriodicRuntimeEvidenceResolution:
        unresolved = list(canonical.unresolved)
        evidence = list(canonical.evidence)

        cadence = canonical.cadence_seconds
        duration = canonical.duration_seconds
        if canonical.timing is None or cadence is None:
            unresolved.append(
                f"{canonical.source_name} coefficient {canonical.coefficient_number}: "
                "canonical periodic cadence is unavailable"
            )
        if duration is None:
            unresolved.append(
                f"{canonical.source_name} coefficient {canonical.coefficient_number}: "
                "canonical active duration is unavailable"
            )

        if observation is None:
            unresolved.extend(
                self._missing_observation_messages(
                    canonical.source_name,
                    canonical.coefficient_number,
                    repeated_applications=repeated_applications,
                    first_tick=True,
                    expiry=True,
                    refresh=repeated_applications,
                )
            )
            return self._result(canonical, None, evidence, unresolved)

        if (
            observation.source_name.casefold() != canonical.source_name.casefold()
            or observation.coefficient_number != canonical.coefficient_number
        ):
            unresolved.append(
                f"{canonical.source_name} coefficient {canonical.coefficient_number}: "
                "reviewed runtime observation identity does not match canonical component"
            )
            return self._result(canonical, None, evidence, unresolved)

        missing_first = observation.first_tick_offset_seconds is None
        missing_expiry = observation.tick_on_expiry_boundary is None
        missing_refresh = repeated_applications and observation.refresh_policy is None
        unresolved.extend(
            self._missing_observation_messages(
                canonical.source_name,
                canonical.coefficient_number,
                repeated_applications=repeated_applications,
                first_tick=missing_first,
                expiry=missing_expiry,
                refresh=missing_refresh,
            )
        )

        for item in observation.provenance:
            evidence.append(f"reviewed runtime observation: {item}")
        if observation.game_version:
            evidence.append(f"reviewed runtime game version: {observation.game_version}")
        if observation.magnitude_policy is not None:
            evidence.append(
                "reviewed periodic magnitude policy: "
                + observation.magnitude_policy.value
            )

        if unresolved or cadence is None or duration is None:
            return self._result(canonical, None, evidence, unresolved)

        assert observation.first_tick_offset_seconds is not None
        assert observation.tick_on_expiry_boundary is not None
        runtime = RotationHealerPeriodicRuntimeEvidence(
            source_name=canonical.source_name,
            coefficient_number=canonical.coefficient_number,
            duration_seconds=float(duration),
            tick_interval_seconds=float(cadence),
            first_tick_offset_seconds=float(observation.first_tick_offset_seconds),
            tick_on_expiry_boundary=bool(observation.tick_on_expiry_boundary),
            refresh_policy=(
                observation.refresh_policy if repeated_applications else None
            ),
            magnitude_policy=observation.magnitude_policy,
        )
        return self._result(canonical, runtime, evidence, unresolved)

    @staticmethod
    def _missing_observation_messages(
        source_name: str,
        coefficient_number: int,
        *,
        repeated_applications: bool,
        first_tick: bool,
        expiry: bool,
        refresh: bool,
    ) -> tuple[str, ...]:
        prefix = f"{source_name} coefficient {coefficient_number}: "
        messages: list[str] = []
        if first_tick:
            messages.append(prefix + "first-tick offset is not canonically/reviewedly verified")
        if expiry:
            messages.append(prefix + "tick-at-expiry boundary behavior is not verified")
        if refresh and repeated_applications:
            messages.append(prefix + "refresh/recast behavior for repeated applications is not verified")
        return tuple(messages)

    @staticmethod
    def _result(
        canonical: RotationHealerCanonicalPeriodicTimingResolution,
        runtime: RotationHealerPeriodicRuntimeEvidence | None,
        evidence: list[str],
        unresolved: list[str],
    ) -> RotationHealerPeriodicRuntimeEvidenceResolution:
        return RotationHealerPeriodicRuntimeEvidenceResolution(
            source_name=canonical.source_name,
            coefficient_number=canonical.coefficient_number,
            runtime_evidence=runtime,
            evidence=tuple(dict.fromkeys(evidence)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
