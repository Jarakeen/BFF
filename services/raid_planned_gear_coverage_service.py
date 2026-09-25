from __future__ import annotations

"""Shared reviewed planned-gear -> raid coverage projection.

Planned gear is raid-lead intent. It can prove that a reviewed set/provider relationship
is part of the plan, but not exact piece count, bar state, proc activation, target
selection, or runtime uptime. Planned evidence is therefore Conditional.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from services.nonability_effect_provider_reference_service import (
    NonAbilityEffectProviderReferenceService,
    canonical_identity,
)
from services.raid_unique_support_set_catalog import UNIQUE_SUPPORT_SET_BY_NAME
from services.saved_build_capability_service import RaidCoverageSnapshot


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _set_lookup_keys(value: object) -> tuple[str, ...]:
    """Return conservative display-name aliases for one ESO set family."""
    text = _clean(value)
    if not text:
        return ()
    keys = [text.casefold()]
    prefix = "perfected "
    if text.casefold().startswith(prefix):
        base = text[len(prefix):].strip()
        if base:
            keys.append(base.casefold())
    return tuple(dict.fromkeys(keys))


@dataclass(frozen=True)
class PlannedGearCoverageProvider:
    seat_id: str
    provider_label: str
    gear_sets: tuple[str, ...]
    source_kind: str = "planned"
    equipped_piece_counts: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        seat = _clean(self.seat_id)
        provider = _clean(self.provider_label) or seat
        gear = tuple(
            dict.fromkeys(
                _clean(value)
                for value in self.gear_sets
                if _clean(value)
            )
        )
        if not seat:
            raise ValueError("planned gear coverage provider requires seat_id")
        object.__setattr__(self, "seat_id", seat)
        object.__setattr__(self, "provider_label", provider)
        object.__setattr__(self, "gear_sets", gear)


class RaidPlannedGearCoverageService:
    """Overlay reviewed planned-set relationships onto static Coverage evidence."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self._reviewed_by_set_cache: dict[str, tuple[object, ...]] | None = None
        self._unique_by_set_cache: dict[str, object] | None = None

    @staticmethod
    def empty_snapshot(effect_names: Iterable[str]) -> RaidCoverageSnapshot:
        names = tuple(
            dict.fromkeys(
                _clean(value)
                for value in effect_names
                if _clean(value)
            )
        )
        return RaidCoverageSnapshot(
            status={name: "unverified" for name in names},
            providers={name: [] for name in names},
            conditional_providers={name: [] for name in names},
        )

    @staticmethod
    def _provider_label(row: PlannedGearCoverageProvider, set_name: str) -> str:
        return f"{row.provider_label} [{row.source_kind}: {set_name}]"

    def _reviewed_by_set(self) -> dict[str, tuple[object, ...]]:
        cached = self._reviewed_by_set_cache
        if cached is not None:
            return cached
        grouped: dict[str, list[object]] = {}
        for item in NonAbilityEffectProviderReferenceService(
            self.database_path
        ).gear():
            grouped.setdefault(item.source_name.casefold(), []).append(item)
        cached = {
            key: tuple(values)
            for key, values in grouped.items()
        }
        self._reviewed_by_set_cache = cached
        return cached

    def _unique_by_set(self) -> dict[str, object]:
        cached = self._unique_by_set_cache
        if cached is None:
            cached = {
                name.casefold(): reference
                for name, reference in UNIQUE_SUPPORT_SET_BY_NAME.items()
            }
            self._unique_by_set_cache = cached
        return cached

    def effects_for_provider(
        self,
        provider: PlannedGearCoverageProvider,
        *,
        effect_names: Iterable[str],
    ) -> tuple[str, ...]:
        """Return reviewed effect names this one planned gear package may provide."""
        names = tuple(
            dict.fromkeys(
                _clean(value)
                for value in effect_names
                if _clean(value)
            )
        )
        snapshot = self.overlay(
            self.empty_snapshot(names),
            (provider,),
            effect_names=names,
        )
        return tuple(
            name
            for name in names
            if snapshot.status.get(name) in {"available", "conditional"}
        )

    def overlay(
        self,
        snapshot: RaidCoverageSnapshot,
        providers: Iterable[PlannedGearCoverageProvider],
        *,
        effect_names: Iterable[str],
    ) -> RaidCoverageSnapshot:
        status = dict(snapshot.status)
        static = {
            name: list(values)
            for name, values in snapshot.providers.items()
        }
        conditional = {
            name: list(values)
            for name, values in snapshot.conditional_providers.items()
        }

        display_by_effect_key = {
            canonical_identity(name): _clean(name)
            for name in effect_names
            if _clean(name)
        }
        reviewed_by_set = self._reviewed_by_set()
        unique_by_set = self._unique_by_set()

        for row in tuple(providers):
            if not isinstance(row, PlannedGearCoverageProvider):
                raise TypeError(
                    "planned gear coverage requires PlannedGearCoverageProvider rows"
                )
            for set_name in row.gear_sets:
                label = self._provider_label(row, set_name)
                keys = _set_lookup_keys(set_name)
                if not keys:
                    continue
                equipped = row.source_kind == "saved build"
                piece_counts = {
                    key: count
                    for name, count in row.equipped_piece_counts
                    for key in _set_lookup_keys(name)
                }
                count = max((piece_counts.get(key, 0) for key in keys), default=0)
                if equipped and count == 0:
                    continue

                unique = next(
                    (
                        unique_by_set[key]
                        for key in keys
                        if key in unique_by_set
                    ),
                    None,
                ) if not equipped else None
                if unique is not None:
                    effect_name = unique.name
                    if effect_name in display_by_effect_key.values():
                        status.setdefault(effect_name, "unverified")
                        static.setdefault(effect_name, [])
                        conditional.setdefault(effect_name, [])
                        if label not in conditional[effect_name]:
                            conditional[effect_name].append(label)

                references = []
                for key in keys:
                    references.extend(reviewed_by_set.get(key, ()))
                seen_reference_ids: set[tuple[str, str]] = set()
                for reference in references:
                    if equipped and (not reference.piece_count or count < reference.piece_count):
                        continue
                    identity = (reference.source_name.casefold(), reference.effect_key)
                    if identity in seen_reference_ids:
                        continue
                    seen_reference_ids.add(identity)
                    effect_name = display_by_effect_key.get(reference.effect_key)
                    if effect_name is None:
                        continue
                    status.setdefault(effect_name, "unverified")
                    static.setdefault(effect_name, [])
                    conditional.setdefault(effect_name, [])
                    if label not in conditional[effect_name]:
                        conditional[effect_name].append(label)

        for name in tuple(status):
            if static.get(name):
                status[name] = "available"
            elif conditional.get(name):
                status[name] = "conditional"

        return RaidCoverageSnapshot(status, static, conditional)


__all__ = [
    "PlannedGearCoverageProvider",
    "RaidPlannedGearCoverageService",
]
