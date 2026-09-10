from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from services.rotation_healer_canonical_periodic_timing_service import (
    RotationHealerCanonicalPeriodicTimingService,
    RotationHealerCanonicalPeriodicTimingResolution,
)
from services.rotation_healer_periodic_runtime_observation_service import (
    RotationHealerPeriodicObservedResolution,
    RotationHealerPeriodicObservedSample,
    RotationHealerPeriodicRuntimeObservationService,
)


@dataclass(frozen=True)
class RotationHealerPeriodicObservationFixtureEntry:
    sample: RotationHealerPeriodicObservedSample
    canonical: RotationHealerCanonicalPeriodicTimingResolution
    observed: RotationHealerPeriodicObservedResolution


@dataclass(frozen=True)
class RotationHealerPeriodicObservationFixtureReport:
    source_path: str
    schema_version: int
    entries: tuple[RotationHealerPeriodicObservationFixtureEntry, ...]
    unresolved: tuple[str, ...]

    @property
    def reviewed_sample_observations(self):
        """Return each explicitly reviewed sample observation without aggregation."""
        return tuple(
            entry.observed.observation
            for entry in self.entries
            if entry.observed.observation is not None
        )

    @property
    def reviewed_observations(self):
        """Return consumer-ready consensus observations grouped by component/version.

        Individual reviewed samples remain available through
        ``reviewed_sample_observations`` and ``entries`` for evidence inspection.
        Downstream runtime consumers receive one consensus observation per canonical
        component and game version so file ordering cannot choose a runtime fact.
        Groups that fail consensus are omitted here and remain visible through the
        consensus audit and entry-level unresolved evidence.
        """
        from services.rotation_healer_periodic_observation_consensus_service import (
            RotationHealerPeriodicObservationConsensusService,
        )

        groups: dict[tuple[str, int, str | None], list[RotationHealerPeriodicObservationFixtureEntry]] = {}
        for entry in self.entries:
            key = (
                entry.sample.source_name.casefold(),
                int(entry.sample.coefficient_number),
                entry.sample.game_version,
            )
            groups.setdefault(key, []).append(entry)

        service = RotationHealerPeriodicObservationConsensusService()
        observations = []
        for key in sorted(groups, key=lambda item: (item[0], item[1], item[2] or "")):
            resolution = service.resolve(tuple(groups[key]))
            if resolution.ready and resolution.observation is not None:
                observations.append(resolution.observation)
        return tuple(observations)


class RotationHealerPeriodicObservationFixtureService:
    """Load reviewed timestamp fixtures and bind them to canonical HoT timing.

    Fixture data is observational evidence only. Canonical component identity,
    duration, and cadence remain owned by the existing healer timing services.
    A fixture can corroborate those facts or conflict with them, but it cannot
    silently replace them.

    Extractor-produced fixtures may explicitly carry ``review_status=candidate``.
    Those are rejected until a reviewer intentionally changes the status to
    ``reviewed`` after checking the event pairing. Legacy hand-reviewed schema-v1
    fixtures that omit the field remain accepted for backward compatibility.
    """

    SCHEMA_VERSION = 1

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.canonical_timing = RotationHealerCanonicalPeriodicTimingService(
            self.database_path
        )
        self.observation_service = RotationHealerPeriodicRuntimeObservationService()

    def load(self, path: str | Path) -> RotationHealerPeriodicObservationFixtureReport:
        source_path = Path(path)
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("healer runtime observation fixture root must be an object")

        schema_version = int(payload.get("schema_version", 0))
        if schema_version != self.SCHEMA_VERSION:
            raise ValueError(
                f"unsupported healer runtime observation schema_version: {schema_version}"
            )

        review_status = str(payload.get("review_status") or "").strip().casefold()
        if review_status and review_status != "reviewed":
            raise ValueError(
                "healer runtime observation fixture is not reviewed; "
                f"review_status={review_status!r}"
            )

        default_game_version = str(payload.get("game_version") or "").strip() or None
        raw_samples = payload.get("samples")
        if not isinstance(raw_samples, list):
            raise ValueError("healer runtime observation fixture samples must be a list")

        entries: list[RotationHealerPeriodicObservationFixtureEntry] = []
        unresolved: list[str] = []

        for index, raw in enumerate(raw_samples, start=1):
            if not isinstance(raw, dict):
                unresolved.append(f"sample {index}: entry must be an object")
                continue
            try:
                sample = self._sample_from_mapping(
                    raw,
                    default_game_version=default_game_version,
                )
            except (KeyError, TypeError, ValueError) as exc:
                unresolved.append(f"sample {index}: {exc}")
                continue

            canonical = self.canonical_timing.resolve(
                source_name=sample.source_name,
                coefficient_number=sample.coefficient_number,
            )
            if not canonical.timing_ready_for_runtime_binding:
                messages = canonical.unresolved or (
                    "canonical cadence/duration is not runtime-ready",
                )
                unresolved.extend(
                    f"sample {index} {sample.source_name} coefficient {sample.coefficient_number}: {message}"
                    for message in messages
                )
                entries.append(
                    RotationHealerPeriodicObservationFixtureEntry(
                        sample=sample,
                        canonical=canonical,
                        observed=RotationHealerPeriodicObservedResolution(
                            observation=None,
                            evidence=(),
                            unresolved=tuple(messages),
                        ),
                    )
                )
                continue

            assert canonical.duration_seconds is not None
            assert canonical.cadence_seconds is not None
            observed = self.observation_service.resolve(
                sample=sample,
                canonical_duration_seconds=canonical.duration_seconds,
                canonical_cadence_seconds=canonical.cadence_seconds,
            )
            unresolved.extend(
                f"sample {index} {sample.source_name} coefficient {sample.coefficient_number}: {message}"
                for message in observed.unresolved
            )
            entries.append(
                RotationHealerPeriodicObservationFixtureEntry(
                    sample=sample,
                    canonical=canonical,
                    observed=observed,
                )
            )

        return RotationHealerPeriodicObservationFixtureReport(
            source_path=str(source_path),
            schema_version=schema_version,
            entries=tuple(entries),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def _sample_from_mapping(
        raw: dict,
        *,
        default_game_version: str | None,
    ) -> RotationHealerPeriodicObservedSample:
        provenance = raw.get("provenance")
        if isinstance(provenance, str):
            provenance = [provenance]
        if not isinstance(provenance, list):
            raise ValueError("provenance must be a string or list of strings")

        ticks = raw.get("observed_tick_times_seconds")
        if not isinstance(ticks, list):
            raise ValueError("observed_tick_times_seconds must be a list")

        return RotationHealerPeriodicObservedSample(
            source_name=str(raw["source_name"]),
            coefficient_number=int(raw["coefficient_number"]),
            activation_time_seconds=float(raw["activation_time_seconds"]),
            observed_tick_times_seconds=tuple(float(value) for value in ticks),
            observation_end_seconds=float(raw["observation_end_seconds"]),
            provenance=tuple(str(value) for value in provenance),
            game_version=(
                str(raw.get("game_version") or "").strip()
                or default_game_version
            ),
        )
