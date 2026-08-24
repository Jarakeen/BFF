from __future__ import annotations

from dataclasses import dataclass

from .role import Role
from .support_effect import SupportEffect
from .roster_capability_resolver import RosterCapabilityProvider


@dataclass(frozen=True)
class CoverageProvider:
    """One roster member capable of providing a specific effect."""

    character_name: str
    role: Role
    effect: SupportEffect


@dataclass(frozen=True)
class CoverageEntry:
    """
    One logical capability and every roster member capable of providing it.

    Providers are preserved independently. No magnitudes, durations,
    target counts, or other effect metadata are merged here.
    """

    effect_name: str
    providers: tuple[CoverageProvider, ...]


class CoverageReport:
    """Read-only result of roster capability coverage analysis."""

    def __init__(
        self,
        entries: tuple[CoverageEntry, ...],
    ) -> None:
        self._entries = entries

    def all(self) -> tuple[CoverageEntry, ...]:
        return self._entries

    def for_effect(self, effect_name: str) -> CoverageEntry | None:
        for entry in self._entries:
            if entry.effect_name == effect_name:
                return entry
        return None

    def effect_names(self) -> tuple[str, ...]:
        return tuple(entry.effect_name for entry in self._entries)


class RosterCoverageAnalyzer:
    """
    Analyze the capabilities already resolved for a roster.

    This layer only organizes existing capability evidence. It does not
    decide whether an effect is required, sufficient, optimal, redundant,
    or useful for a particular encounter.
    """

    def analyze(
        self,
        roster_capabilities: dict[
            str,
            tuple[RosterCapabilityProvider, ...],
        ],
    ) -> CoverageReport:
        entries: list[CoverageEntry] = []

        for effect_name in sorted(roster_capabilities):
            providers = tuple(
                CoverageProvider(
                    character_name=provider.character_name,
                    role=provider.role,
                    effect=provider.effect,
                )
                for provider in roster_capabilities[effect_name]
            )

            entries.append(
                CoverageEntry(
                    effect_name=effect_name,
                    providers=providers,
                )
            )

        return CoverageReport(tuple(entries))