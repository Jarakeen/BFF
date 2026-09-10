from __future__ import annotations

"""Project explicit ESO Logs aura transitions into shared runtime effect windows.

This adapter is intentionally role-neutral.  It converts translated aura lifecycle
events into ``RuntimeEffectActiveWindow`` instances that any BFF consumer can query
through the canonical runtime-window / combat-state snapshot contracts.

Only explicit observed transitions are accepted.  Numeric ability IDs are not promoted
into semantic effect identity, and an open aura without an observed removal does not
receive an invented end time.
"""

from dataclasses import dataclass
from typing import Iterable

from minmax.runtime_effect_window import RuntimeEffectActiveWindow, order_runtime_effect_windows


_OPEN_TYPES = {"applybuff", "applydebuff"}
_REFRESH_TYPES = {"refreshbuff", "refreshdebuff"}
_CLOSE_TYPES = {"removebuff", "removedebuff"}


@dataclass(frozen=True, slots=True)
class EsoLogsRuntimeEffectWindowResult:
    windows: tuple[RuntimeEffectActiveWindow, ...]
    unresolved: tuple[str, ...] = ()


class EsoLogsRuntimeEffectWindowService:
    """Build bounded shared runtime windows from explicit translated aura events."""

    def build(
        self,
        events: Iterable[dict],
        *,
        fight_start_time_ms: float,
        effect_names: Iterable[str] = (),
    ) -> EsoLogsRuntimeEffectWindowResult:
        start_ms = float(fight_start_time_ms)
        wanted_names = {
            str(name).strip().casefold()
            for name in effect_names
            if str(name or "").strip()
        }
        rows = tuple(
            sorted(
                (row for row in events if isinstance(row, dict)),
                key=lambda row: (self._timestamp(row), self._sequence(row)),
            )
        )

        # key = translated semantic name + explicit source/target actor identity.
        # Actor IDs remain runtime identities here; they are never canonical skill IDs.
        active: dict[tuple[str, int | None, int | None], tuple[dict, float]] = {}
        windows: list[RuntimeEffectActiveWindow] = []
        unresolved: list[str] = []

        for row in rows:
            event_type = self._event_type(row)
            if event_type not in (_OPEN_TYPES | _REFRESH_TYPES | _CLOSE_TYPES):
                continue

            name = self._ability_name(row)
            if wanted_names and name and name.casefold() not in wanted_names:
                continue
            if not name:
                # When a caller supplied an explicit semantic filter, an unnamed aura
                # cannot match that filter and is irrelevant to this projection.
                if wanted_names:
                    continue
                unresolved.append(
                    "Aura transition with no translated ability name was not projected into runtime effect state."
                )
                continue

            source_id = self._int_or_none(row.get("sourceID"))
            target_id = self._int_or_none(row.get("targetID"))
            key = (name, source_id, target_id)
            timestamp_ms = self._timestamp(row)
            time_seconds = max(0.0, (timestamp_ms - start_ms) / 1000.0)

            if event_type in _OPEN_TYPES:
                if key in active:
                    unresolved.append(
                        f"Duplicate open aura transition for {name} source={source_id} target={target_id}; prior open state was preserved."
                    )
                    continue
                active[key] = (row, time_seconds)
                continue

            if event_type in _REFRESH_TYPES:
                # A refresh proves the aura is active at this timestamp.  If an earlier
                # explicit open exists, continuity is preserved.  If it does not, the
                # refresh becomes the earliest defensible observed start.
                active.setdefault(key, (row, time_seconds))
                continue

            opened = active.pop(key, None)
            if opened is None:
                unresolved.append(
                    f"Aura removal for {name} source={source_id} target={target_id} had no observed open transition."
                )
                continue

            open_row, open_seconds = opened
            if time_seconds <= open_seconds:
                unresolved.append(
                    f"Aura removal for {name} source={source_id} target={target_id} did not occur after its observed open transition."
                )
                continue

            windows.append(
                RuntimeEffectActiveWindow(
                    effect_name=name,
                    source=self._source_identity(source_id),
                    start_time_seconds=open_seconds,
                    end_time_seconds=time_seconds,
                    target=self._target_identity(target_id),
                    sequence=self._sequence(open_row),
                )
            )

        for (name, source_id, target_id), _opened in active.items():
            unresolved.append(
                f"Open aura {name} source={source_id} target={target_id} had no observed removal; no bounded runtime window was inferred."
            )

        return EsoLogsRuntimeEffectWindowResult(
            windows=order_runtime_effect_windows(windows),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def _event_type(row: dict) -> str:
        return str(row.get("type") or "").strip().casefold()

    @staticmethod
    def _timestamp(row: dict) -> float:
        try:
            return float(row.get("timestamp", 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _sequence(row: dict) -> int:
        try:
            value = int(row.get("sequence", 0) or 0)
        except (TypeError, ValueError):
            return 0
        return max(0, value)

    @staticmethod
    def _int_or_none(value) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _ability_name(row: dict) -> str:
        for key in ("abilityName", "name"):
            value = row.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        ability = row.get("ability")
        if isinstance(ability, dict):
            value = ability.get("name")
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    @staticmethod
    def _source_identity(actor_id: int | None) -> str:
        return "esologs:source:unknown" if actor_id is None else f"esologs:actor:{actor_id}"

    @staticmethod
    def _target_identity(actor_id: int | None) -> str | None:
        return None if actor_id is None else f"esologs:actor:{actor_id}"


__all__ = [
    "EsoLogsRuntimeEffectWindowResult",
    "EsoLogsRuntimeEffectWindowService",
]
