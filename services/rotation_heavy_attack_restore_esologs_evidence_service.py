from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from services.esologs_event_interpreter import EsoLogsEventInterpreter, SemanticEventKind


@dataclass(frozen=True)
class RotationHeavyAttackRestoreObservation:
    report_code: str
    fight_id: int
    event_index: int
    timestamp: float
    source_id: int | None
    ability_game_id: int | None
    ability_name: str | None
    resource_change: float
    resource_change_type: int | None
    waste: float | None
    max_resource_amount: float | None


@dataclass(frozen=True)
class RotationHeavyAttackRestoreObservationReport:
    observations: tuple[RotationHeavyAttackRestoreObservation, ...]
    unresolved: tuple[str, ...] = ()


class RotationHeavyAttackRestoreEsoLogsEvidenceService:
    """Surface observed positive resource restores for reviewed heavy-attack aliases.

    This is observational evidence only. Caller-supplied names or numeric aliases
    select candidate heavy-attack resource-change events from one explicit ESO Logs
    fight. Numeric log ids are not promoted to canonical skill identity, resource
    type enums are preserved raw, and observed restore amounts are never promoted
    to live game constants by this service.
    """

    def discover(
        self,
        database_path: str | Path,
        *,
        report_code: str,
        fight_id: int,
        ability_names: tuple[str, ...] = (),
        ability_game_ids: tuple[int, ...] = (),
        source_id: int | None = None,
    ) -> RotationHeavyAttackRestoreObservationReport:
        names = frozenset(
            str(value or "").strip().casefold()
            for value in ability_names
            if str(value or "").strip()
        )
        ids = frozenset(int(value) for value in ability_game_ids)
        if not names and not ids:
            raise ValueError(
                "heavy restore observation discovery requires at least one reviewed ability alias"
            )
        report = str(report_code or "").strip()
        if not report:
            raise ValueError("report_code is required")
        fight = int(fight_id)
        if fight < 0:
            raise ValueError("fight_id cannot be negative")

        path = Path(database_path)
        with sqlite3.connect(path) as db:
            db.row_factory = sqlite3.Row
            interpreter = EsoLogsEventInterpreter(db)
            events = interpreter.iter_fight(
                report,
                fight,
                event_kinds={SemanticEventKind.RESOURCE_CHANGE},
            )
            observations: list[RotationHeavyAttackRestoreObservation] = []
            for event in events:
                if source_id is not None and event.source_id != int(source_id):
                    continue
                name_match = (
                    event.ability_name is not None
                    and event.ability_name.strip().casefold() in names
                )
                id_match = (
                    event.ability_game_id is not None
                    and event.ability_game_id in ids
                )
                if not (name_match or id_match):
                    continue
                amount = event.resource_change
                if amount is None or float(amount) <= 0.0:
                    continue
                observations.append(
                    RotationHeavyAttackRestoreObservation(
                        report_code=event.report_code,
                        fight_id=event.fight_id,
                        event_index=event.event_index,
                        timestamp=event.timestamp,
                        source_id=event.source_id,
                        ability_game_id=event.ability_game_id,
                        ability_name=event.ability_name,
                        resource_change=float(amount),
                        resource_change_type=event.resource_change_type,
                        waste=event.waste,
                        max_resource_amount=event.max_resource_amount,
                    )
                )

        unresolved: tuple[str, ...] = ()
        if not observations:
            unresolved = (
                "no positive resource-change events matched the reviewed heavy-attack aliases",
            )
        return RotationHeavyAttackRestoreObservationReport(
            observations=tuple(observations),
            unresolved=unresolved,
        )


__all__ = [
    "RotationHeavyAttackRestoreObservation",
    "RotationHeavyAttackRestoreObservationReport",
    "RotationHeavyAttackRestoreEsoLogsEvidenceService",
]
