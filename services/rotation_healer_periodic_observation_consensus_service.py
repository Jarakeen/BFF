from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import median

from services.rotation_healer_periodic_observation_fixture_service import (
    RotationHealerPeriodicObservationFixtureEntry,
)
from services.rotation_healer_periodic_runtime_evidence_service import (
    RotationHealerReviewedRuntimeObservation,
)


@dataclass(frozen=True)
class RotationHealerPeriodicObservationConsensusResolution:
    source_name: str
    coefficient_number: int
    game_version: str | None
    observation: RotationHealerReviewedRuntimeObservation | None
    sample_count: int
    first_tick_offset_range_seconds: tuple[float, float] | None = None
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.observation is not None and not self.unresolved


class RotationHealerPeriodicObservationConsensusService:
    """Combine repeated reviewed healer runtime samples without hiding disagreement.

    The fixture loader retains one observation per explicitly reviewed sample. This
    service derives a single observational consensus for one canonical component and
    game version. It refuses to merge entries with unresolved runtime conflicts,
    contradictory expiry-boundary evidence, missing first-tick facts, or first-tick
    measurements whose spread exceeds the reviewed observational tolerance.

    The first-tick consensus is the median of the reviewed offsets. Every contributing
    provenance item is preserved and refresh/recast semantics are not inferred here.
    """

    def resolve(
        self,
        entries: tuple[RotationHealerPeriodicObservationFixtureEntry, ...],
        *,
        first_tick_spread_tolerance_seconds: float = 0.1,
    ) -> RotationHealerPeriodicObservationConsensusResolution:
        spread_tolerance = float(first_tick_spread_tolerance_seconds)
        if not math.isfinite(spread_tolerance) or spread_tolerance < 0:
            raise ValueError(
                "first_tick_spread_tolerance_seconds must be finite and non-negative"
            )
        if not entries:
            raise ValueError("healer periodic observation consensus requires entries")

        first = entries[0]
        source_name = first.sample.source_name
        coefficient_number = int(first.sample.coefficient_number)
        game_version = first.sample.game_version
        unresolved: list[str] = []
        evidence: list[str] = []

        for index, entry in enumerate(entries, start=1):
            if (
                entry.sample.source_name.casefold() != source_name.casefold()
                or int(entry.sample.coefficient_number) != coefficient_number
                or entry.sample.game_version != game_version
            ):
                unresolved.append(
                    f"sample {index}: observation identity/version does not match consensus group"
                )
            unresolved.extend(
                f"sample {index}: {message}" for message in entry.observed.unresolved
            )

        prefix = f"{source_name} coefficient {coefficient_number}: "
        if unresolved:
            return self._result(
                source_name=source_name,
                coefficient_number=coefficient_number,
                game_version=game_version,
                sample_count=len(entries),
                first_tick_range=None,
                observation=None,
                evidence=evidence,
                unresolved=unresolved,
            )

        observations = tuple(entry.observed.observation for entry in entries)
        if any(observation is None for observation in observations):
            unresolved.append(prefix + "one or more reviewed samples produced no runtime observation")
            return self._result(
                source_name=source_name,
                coefficient_number=coefficient_number,
                game_version=game_version,
                sample_count=len(entries),
                first_tick_range=None,
                observation=None,
                evidence=evidence,
                unresolved=unresolved,
            )

        reviewed = tuple(observation for observation in observations if observation is not None)
        first_tick_offsets = tuple(
            observation.first_tick_offset_seconds for observation in reviewed
        )
        if any(value is None for value in first_tick_offsets):
            unresolved.append(prefix + "first-tick offset is missing from one or more reviewed samples")
            first_tick_range = None
        else:
            offsets = tuple(float(value) for value in first_tick_offsets if value is not None)
            first_tick_range = (min(offsets), max(offsets))
            spread = first_tick_range[1] - first_tick_range[0]
            if spread > spread_tolerance:
                unresolved.append(
                    prefix
                    + f"reviewed first-tick offsets disagree beyond {spread_tolerance:g}s tolerance "
                    + f"({first_tick_range[0]:g}s-{first_tick_range[1]:g}s observed)"
                )

        expiry_values = tuple(
            observation.tick_on_expiry_boundary for observation in reviewed
        )
        if any(value is None for value in expiry_values):
            unresolved.append(prefix + "expiry-boundary behavior is missing from one or more reviewed samples")
        elif len(set(bool(value) for value in expiry_values)) != 1:
            unresolved.append(prefix + "reviewed expiry-boundary observations disagree")

        refresh_values = {
            observation.refresh_policy
            for observation in reviewed
            if observation.refresh_policy is not None
        }
        if len(refresh_values) > 1:
            unresolved.append(prefix + "reviewed refresh/recast observations disagree")

        if unresolved or first_tick_range is None:
            return self._result(
                source_name=source_name,
                coefficient_number=coefficient_number,
                game_version=game_version,
                sample_count=len(entries),
                first_tick_range=first_tick_range,
                observation=None,
                evidence=evidence,
                unresolved=unresolved,
            )

        offsets = tuple(float(value) for value in first_tick_offsets if value is not None)
        consensus_first_tick = float(median(offsets))
        consensus_expiry = bool(expiry_values[0])
        consensus_refresh = next(iter(refresh_values), None)

        for observation in reviewed:
            evidence.extend(observation.provenance)
        evidence.extend(
            (
                f"consensus from {len(reviewed)} explicitly reviewed isolated activation sample(s)",
                f"reviewed first-tick offsets range {first_tick_range[0]:g}s-{first_tick_range[1]:g}s; median {consensus_first_tick:g}s",
                "reviewed expiry-boundary observations agree: "
                + ("tick present" if consensus_expiry else "no tick present"),
            )
        )
        if consensus_refresh is None:
            evidence.append("refresh/recast semantics remain unresolved by this consensus")

        observation = RotationHealerReviewedRuntimeObservation(
            source_name=source_name,
            coefficient_number=coefficient_number,
            first_tick_offset_seconds=consensus_first_tick,
            tick_on_expiry_boundary=consensus_expiry,
            refresh_policy=consensus_refresh,
            provenance=tuple(dict.fromkeys(evidence)),
            game_version=game_version,
        )
        return self._result(
            source_name=source_name,
            coefficient_number=coefficient_number,
            game_version=game_version,
            sample_count=len(entries),
            first_tick_range=first_tick_range,
            observation=observation,
            evidence=evidence,
            unresolved=unresolved,
        )

    @staticmethod
    def _result(
        *,
        source_name: str,
        coefficient_number: int,
        game_version: str | None,
        sample_count: int,
        first_tick_range: tuple[float, float] | None,
        observation: RotationHealerReviewedRuntimeObservation | None,
        evidence: list[str],
        unresolved: list[str],
    ) -> RotationHealerPeriodicObservationConsensusResolution:
        return RotationHealerPeriodicObservationConsensusResolution(
            source_name=source_name,
            coefficient_number=coefficient_number,
            game_version=game_version,
            observation=observation,
            sample_count=sample_count,
            first_tick_offset_range_seconds=first_tick_range,
            evidence=tuple(dict.fromkeys(evidence)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "RotationHealerPeriodicObservationConsensusResolution",
    "RotationHealerPeriodicObservationConsensusService",
]
