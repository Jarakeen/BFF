from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

from services.esologs_event_interpreter import SemanticEventKind
from services.esologs_json_adapter import EsoLogsJsonEventInterpreter, EsoLogsJsonFight
from services.rotation_healer_canonical_periodic_timing_service import (
    RotationHealerCanonicalPeriodicTimingService,
)
from services.rotation_healer_periodic_runtime_observation_service import (
    RotationHealerPeriodicObservedSample,
)


class RotationHealerEsoLogsTimestampUnit(str, Enum):
    MILLISECONDS = "milliseconds"
    SECONDS = "seconds"

    @property
    def seconds_scale(self) -> float:
        return 0.001 if self is self.MILLISECONDS else 1.0


@dataclass(frozen=True)
class RotationHealerEsoLogsObservationTarget:
    source_name: str
    coefficient_number: int
    ability_game_id: int


DF_HEALER_U50_OBSERVATION_TARGETS = (
    RotationHealerEsoLogsObservationTarget("Budding Seeds", 2, 93807),
    RotationHealerEsoLogsObservationTarget("Radiating Regeneration", 1, 41288),
    RotationHealerEsoLogsObservationTarget("Illustrious Healing", 1, 41255),
    RotationHealerEsoLogsObservationTarget("Energy Orb", 1, 43447),
    RotationHealerEsoLogsObservationTarget("Echoing Vigor", 1, 63247),
)


@dataclass(frozen=True)
class RotationHealerEsoLogsObservationCandidate:
    target: RotationHealerEsoLogsObservationTarget
    sample: RotationHealerPeriodicObservedSample
    activation_event_index: int
    raw_periodic_heal_event_count: int


@dataclass(frozen=True)
class RotationHealerEsoLogsObservationExtractionReport:
    source_path: str
    report_code: str
    fight_id: int
    caster_id: int
    timestamp_unit: RotationHealerEsoLogsTimestampUnit
    candidates: tuple[RotationHealerEsoLogsObservationCandidate, ...]
    unresolved: tuple[str, ...] = ()

    def to_candidate_fixture_payload(self, *, game_version: str = "U50") -> dict:
        return {
            "schema_version": 1,
            "review_status": "candidate",
            "game_version": str(game_version),
            "source": {
                "kind": "esologs_raw_export",
                "path": self.source_path,
                "report_code": self.report_code,
                "fight_id": self.fight_id,
                "caster_id": self.caster_id,
                "timestamp_unit": self.timestamp_unit.value,
            },
            "samples": [
                {
                    "source_name": item.sample.source_name,
                    "coefficient_number": item.sample.coefficient_number,
                    "activation_time_seconds": item.sample.activation_time_seconds,
                    "observed_tick_times_seconds": list(item.sample.observed_tick_times_seconds),
                    "observation_end_seconds": item.sample.observation_end_seconds,
                    "provenance": list(item.sample.provenance),
                    "game_version": item.sample.game_version,
                    "candidate_metadata": {
                        "ability_game_id": item.target.ability_game_id,
                        "activation_event_index": item.activation_event_index,
                        "raw_periodic_heal_event_count": item.raw_periodic_heal_event_count,
                    },
                }
                for item in self.candidates
            ],
        }


class RotationHealerEsoLogsObservationExtractor:
    """Extract review candidates for healer HoT micro-timing from raw ESO Logs.

    This service does not promote runtime facts. It only pairs isolated casts with
    same-caster periodic heal events for exact reviewed ability IDs and emits
    candidate samples. The resulting payload is explicitly marked ``candidate``
    and must be human-reviewed before the runtime fixture loader will accept it.

    Multiple recipients healed on the same periodic tick are collapsed to one
    timestamp. Activations recast before canonical expiry are skipped because
    ordinary first-tick/expiry observations must not silently cross unresolved
    reapplication semantics.

    Both the legacy single-report raw export and the research multi-report corpus
    are accepted. A corpus requires an explicit report code because fight ids are
    only unique within a report and must never be resolved by file order.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.canonical_timing = RotationHealerCanonicalPeriodicTimingService(
            self.database_path
        )

    @staticmethod
    def load_fight(
        raw_path: str | Path,
        *,
        fight_id: int,
        report_code: str | None = None,
    ) -> EsoLogsJsonFight:
        path = Path(raw_path)
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        reports = payload.get("reports") if isinstance(payload, dict) else None
        if not isinstance(reports, dict):
            return EsoLogsJsonFight.from_payload(
                payload,
                fight_id=int(fight_id),
                report_code=report_code,
                source_name=str(path),
            )

        requested = str(report_code or "").strip()
        if not requested:
            available = ", ".join(sorted(str(key) for key in reports))
            raise ValueError(
                f"{path}: multi-report ESO Logs corpus requires report_code; "
                f"available reports: {available or '(none)'}"
            )
        report_payload = reports.get(requested)
        if not isinstance(report_payload, dict):
            available = ", ".join(sorted(str(key) for key in reports))
            raise ValueError(
                f"{path}: report {requested!r} is not present in corpus; "
                f"available reports: {available or '(none)'}"
            )
        return EsoLogsJsonFight.from_payload(
            report_payload,
            fight_id=int(fight_id),
            report_code=requested,
            source_name=f"{path} report {requested}",
        )

    def extract(
        self,
        raw_path: str | Path,
        *,
        fight_id: int,
        caster_id: int,
        report_code: str | None = None,
        targets: tuple[RotationHealerEsoLogsObservationTarget, ...] = DF_HEALER_U50_OBSERVATION_TARGETS,
        timestamp_unit: RotationHealerEsoLogsTimestampUnit | str = RotationHealerEsoLogsTimestampUnit.MILLISECONDS,
        game_version: str = "U50",
        expiry_tolerance_seconds: float = 0.02,
    ) -> RotationHealerEsoLogsObservationExtractionReport:
        unit = (
            timestamp_unit
            if isinstance(timestamp_unit, RotationHealerEsoLogsTimestampUnit)
            else RotationHealerEsoLogsTimestampUnit(str(timestamp_unit))
        )
        scale = unit.seconds_scale
        fight = self.load_fight(
            raw_path,
            fight_id=int(fight_id),
            report_code=report_code,
        )
        events = list(EsoLogsJsonEventInterpreter(fight).iter_events())
        fight_observation_end = max((event.timestamp * scale for event in events), default=0.0)

        candidates: list[RotationHealerEsoLogsObservationCandidate] = []
        unresolved: list[str] = []

        for target in targets:
            canonical = self.canonical_timing.resolve(
                source_name=target.source_name,
                coefficient_number=target.coefficient_number,
            )
            if not canonical.timing_ready_for_runtime_binding:
                details = canonical.unresolved or (
                    "canonical cadence/duration is not runtime-ready",
                )
                unresolved.extend(
                    f"{target.source_name} coefficient {target.coefficient_number}: {message}"
                    for message in details
                )
                continue

            assert canonical.duration_seconds is not None
            activations = self._activation_events(
                events,
                caster_id=int(caster_id),
                ability_game_id=target.ability_game_id,
            )
            if not activations:
                unresolved.append(
                    f"{target.source_name}: no matching cast/completecast event for caster {caster_id}"
                )
                continue

            for activation_index, activation in activations:
                activation_seconds = activation.timestamp * scale
                expiry_seconds = activation_seconds + canonical.duration_seconds
                next_activation_seconds = self._next_activation_seconds(
                    activations,
                    after_event_index=activation_index,
                    scale=scale,
                )
                if (
                    next_activation_seconds is not None
                    and next_activation_seconds < expiry_seconds - expiry_tolerance_seconds
                ):
                    unresolved.append(
                        f"{target.source_name} activation event {activation_index}: skipped because another activation occurs before canonical expiry"
                    )
                    continue

                periodic_heals = [
                    event
                    for event in events
                    if event.event_kind == SemanticEventKind.HEAL
                    and event.source_id == int(caster_id)
                    and event.ability_game_id == target.ability_game_id
                    and (event.tick is True or event.raw_event_type == "hot")
                    and activation_seconds - expiry_tolerance_seconds
                    <= event.timestamp * scale
                    <= expiry_seconds + expiry_tolerance_seconds
                ]
                tick_times = tuple(
                    sorted(
                        {
                            round(event.timestamp * scale, 6)
                            for event in periodic_heals
                        }
                    )
                )
                if not tick_times:
                    unresolved.append(
                        f"{target.source_name} activation event {activation_index}: no same-caster periodic heal events found within canonical active window"
                    )
                    continue

                sample = RotationHealerPeriodicObservedSample(
                    source_name=target.source_name,
                    coefficient_number=target.coefficient_number,
                    activation_time_seconds=round(activation_seconds, 6),
                    observed_tick_times_seconds=tick_times,
                    observation_end_seconds=round(
                        min(
                            fight_observation_end,
                            expiry_seconds + expiry_tolerance_seconds,
                        ),
                        6,
                    ),
                    provenance=(
                        f"candidate extracted from ESO Logs raw export {fight.report_code} fight {fight.fight_id}",
                        f"casterID={int(caster_id)} abilityGameID={target.ability_game_id} activation_event_index={activation_index}",
                        "same-caster periodic heal events only; same-timestamp recipient heals deduplicated",
                    ),
                    game_version=str(game_version),
                )
                candidates.append(
                    RotationHealerEsoLogsObservationCandidate(
                        target=target,
                        sample=sample,
                        activation_event_index=activation_index,
                        raw_periodic_heal_event_count=len(periodic_heals),
                    )
                )

        return RotationHealerEsoLogsObservationExtractionReport(
            source_path=str(Path(raw_path)),
            report_code=fight.report_code,
            fight_id=fight.fight_id,
            caster_id=int(caster_id),
            timestamp_unit=unit,
            candidates=tuple(candidates),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def _activation_events(events, *, caster_id: int, ability_game_id: int):
        matching = [
            (event.event_index, event)
            for event in events
            if event.event_kind == SemanticEventKind.CAST
            and event.source_id == caster_id
            and event.ability_game_id == ability_game_id
            and event.raw_event_type in {"cast", "completecast"}
        ]

        deduped: list[tuple[int, object]] = []
        seen_tracks: set[int] = set()
        seen_fallback: set[tuple[float, str]] = set()
        for event_index, event in matching:
            if event.cast_track_id is not None:
                if event.cast_track_id in seen_tracks:
                    continue
                seen_tracks.add(event.cast_track_id)
            else:
                key = (float(event.timestamp), str(event.raw_event_type))
                if key in seen_fallback:
                    continue
                seen_fallback.add(key)
            deduped.append((event_index, event))
        return tuple(deduped)

    @staticmethod
    def _next_activation_seconds(activations, *, after_event_index: int, scale: float):
        for event_index, event in activations:
            if event_index > after_event_index:
                return float(event.timestamp) * scale
        return None
