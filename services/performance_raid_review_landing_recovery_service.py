from __future__ import annotations

"""Measure observed role recovery after an encounter landing boundary.

The service is intentionally generic.  A caller supplies reviewed semantic recovery
signals and their translated ESO Logs ability-name evidence.  Numeric ability IDs do
not become canonical identities here.
"""

from dataclasses import dataclass
from typing import Iterable

from services.rotation_lokkestiiz_landing_clock_service import EncounterObservedClockBoundary


@dataclass(frozen=True, slots=True)
class RaidReviewRecoveryActor:
    actor_id: int
    actor_label: str
    role: str
    member_key: str = ""


@dataclass(frozen=True, slots=True)
class RaidReviewRecoverySignal:
    semantic_key: str
    label: str
    role: str
    event_types: tuple[str, ...]
    ability_names: tuple[str, ...] = ()
    require_boss_target: bool = False
    reviewed: bool = True

    def __post_init__(self) -> None:
        if self.reviewed and not self.semantic_key.strip():
            raise ValueError("Reviewed recovery signals require a semantic_key.")
        if self.reviewed and not self.event_types:
            raise ValueError("Reviewed recovery signals require at least one event type.")
        if self.reviewed and not self.ability_names and not self.require_boss_target:
            raise ValueError(
                "Reviewed recovery signals require translated ability-name evidence or a boss-target rule."
            )


@dataclass(frozen=True, slots=True)
class RaidReviewLandingRecoveryObservation:
    report_code: str
    fight_id: int
    occurrence: int
    actor_id: int
    actor_label: str
    role: str
    member_key: str
    landing_seconds: float
    recovery_seconds: float
    delay_seconds: float
    signal_semantic_key: str
    signal_label: str
    evidence_ability_name: str = ""


@dataclass(frozen=True, slots=True)
class RaidReviewLandingRecoveryResult:
    observations: tuple[RaidReviewLandingRecoveryObservation, ...]
    unresolved: tuple[str, ...] = ()


class PerformanceRaidReviewLandingRecoveryService:
    """Resolve first reviewed role action after each observed landing."""

    _DEFAULT_EVENT_TYPES = {"cast", "damage", "calculateddamage", "applydebuff", "applybuff"}

    def measure(
        self,
        *,
        report_code: str,
        fight_id: int,
        fight_start_time_ms: float,
        events: Iterable[dict],
        landing_boundaries: Iterable[EncounterObservedClockBoundary],
        actors: Iterable[RaidReviewRecoveryActor],
        signals: Iterable[RaidReviewRecoverySignal],
        boss_actor_id: int | None = None,
        max_delay_seconds: float = 15.0,
    ) -> RaidReviewLandingRecoveryResult:
        rows = tuple(event for event in events if isinstance(event, dict))
        actor_rows = tuple(actors)
        reviewed_signals = tuple(signal for signal in signals if signal.reviewed)
        boundaries = tuple(
            sorted(
                (
                    boundary
                    for boundary in landing_boundaries
                    if boundary.fact_key == "aerial_onslaught_flight" and boundary.boundary == "end"
                ),
                key=lambda item: (item.occurrence, item.time_seconds),
            )
        )
        unresolved: list[str] = []
        observations: list[RaidReviewLandingRecoveryObservation] = []

        if not boundaries:
            return RaidReviewLandingRecoveryResult((), ("No observed landing boundaries were supplied.",))
        if not actor_rows:
            return RaidReviewLandingRecoveryResult((), ("No raid actors were supplied for landing recovery.",))
        if not reviewed_signals:
            return RaidReviewLandingRecoveryResult((), ("No reviewed recovery signals were supplied.",))

        start_ms = float(fight_start_time_ms)
        max_delay = max(0.0, float(max_delay_seconds))

        for actor in actor_rows:
            role = self._canonical_role(actor.role)
            role_signals = tuple(
                signal for signal in reviewed_signals if self._canonical_role(signal.role) == role
            )
            if not role_signals:
                unresolved.append(f"No reviewed landing-recovery signal is defined for {actor.actor_label} ({role}).")
                continue

            for boundary in boundaries:
                candidate = self._first_matching_event(
                    rows,
                    actor_id=int(actor.actor_id),
                    landing_seconds=float(boundary.time_seconds),
                    fight_start_time_ms=start_ms,
                    signals=role_signals,
                    boss_actor_id=boss_actor_id,
                    max_delay_seconds=max_delay,
                )
                if candidate is None:
                    unresolved.append(
                        f"No reviewed {role} recovery evidence for {actor.actor_label} after landing {boundary.occurrence} within {max_delay:.1f}s."
                    )
                    continue

                event, signal, recovery_seconds = candidate
                observations.append(
                    RaidReviewLandingRecoveryObservation(
                        report_code=str(report_code),
                        fight_id=int(fight_id),
                        occurrence=int(boundary.occurrence),
                        actor_id=int(actor.actor_id),
                        actor_label=str(actor.actor_label),
                        role=role,
                        member_key=str(actor.member_key or ""),
                        landing_seconds=float(boundary.time_seconds),
                        recovery_seconds=recovery_seconds,
                        delay_seconds=max(0.0, recovery_seconds - float(boundary.time_seconds)),
                        signal_semantic_key=signal.semantic_key,
                        signal_label=signal.label or signal.semantic_key,
                        evidence_ability_name=self._ability_name(event),
                    )
                )

        observations.sort(key=lambda item: (item.occurrence, item.role, item.actor_label.casefold()))
        return RaidReviewLandingRecoveryResult(tuple(observations), tuple(unresolved))

    def _first_matching_event(
        self,
        rows: tuple[dict, ...],
        *,
        actor_id: int,
        landing_seconds: float,
        fight_start_time_ms: float,
        signals: tuple[RaidReviewRecoverySignal, ...],
        boss_actor_id: int | None,
        max_delay_seconds: float,
    ) -> tuple[dict, RaidReviewRecoverySignal, float] | None:
        lower_ms = fight_start_time_ms + landing_seconds * 1000.0
        upper_ms = lower_ms + max_delay_seconds * 1000.0
        candidates: list[tuple[float, dict, RaidReviewRecoverySignal]] = []

        for event in rows:
            if self._int_or_none(event.get("sourceID")) != actor_id:
                continue
            timestamp = self._timestamp(event)
            if timestamp < lower_ms or timestamp > upper_ms:
                continue
            event_type = self._event_type(event)
            ability_name = self._ability_name(event).casefold()

            for signal in signals:
                allowed_types = {value.strip().casefold() for value in signal.event_types if value.strip()}
                if event_type not in allowed_types:
                    continue
                if signal.require_boss_target:
                    if boss_actor_id is None:
                        continue
                    if self._int_or_none(event.get("targetID")) != int(boss_actor_id):
                        continue
                    if event_type in {"damage", "calculateddamage"} and self._amount(event) <= 0:
                        continue
                names = {value.strip().casefold() for value in signal.ability_names if value.strip()}
                if names and ability_name not in names:
                    continue
                candidates.append((timestamp, event, signal))

        if not candidates:
            return None
        timestamp, event, signal = min(candidates, key=lambda item: (item[0], item[2].semantic_key))
        return event, signal, max(0.0, (timestamp - fight_start_time_ms) / 1000.0)

    @staticmethod
    def _canonical_role(role: str) -> str:
        value = str(role or "").strip().casefold()
        if value in {"healer", "healing"}:
            return "Healer"
        if value in {"tank", "tanking"}:
            return "Tank"
        return "DPS"

    @staticmethod
    def _event_type(event: dict) -> str:
        return str(event.get("type") or "").strip().casefold()

    @staticmethod
    def _timestamp(event: dict) -> float:
        try:
            return float(event.get("timestamp", 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _int_or_none(value) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _amount(event: dict) -> float:
        try:
            return float(event.get("amount", 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _ability_name(event: dict) -> str:
        for key in ("abilityName", "name"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        ability = event.get("ability")
        if isinstance(ability, dict):
            value = ability.get("name")
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""


__all__ = [
    "PerformanceRaidReviewLandingRecoveryService",
    "RaidReviewLandingRecoveryObservation",
    "RaidReviewLandingRecoveryResult",
    "RaidReviewRecoveryActor",
    "RaidReviewRecoverySignal",
]
