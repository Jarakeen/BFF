from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from models.build_model import PlayerBuild


@dataclass(frozen=True)
class TeamBuildCapabilitySummary:
    player_name: str
    build_name: str
    resolved_effects: tuple[str, ...]
    capability_gaps: tuple[str, ...]
    conditional_sources: tuple[str, ...]
    boundaries: tuple[str, ...]


@dataclass(frozen=True)
class TeamOptimizationCanonicalAnalysis:
    saved_build_count: int
    recruit_count: int
    build_summaries: tuple[TeamBuildCapabilitySummary, ...]
    capability_providers: tuple[tuple[str, tuple[str, ...]], ...]
    capability_gap_count: int
    conditional_source_count: int
    boundary_count: int

    @property
    def resolved_capability_count(self) -> int:
        return len(self.capability_providers)

    @property
    def is_capability_clean(self) -> bool:
        return self.capability_gap_count == 0


class TeamOptimizationCanonicalAnalysisService:
    """Summarize canonical static capability evidence for one selected team.

    This deliberately stops at the Phase 12.5 boundary. A selected saved build can
    prove static capability availability, conditional source identity, and explicit
    resolution gaps. It cannot prove encounter uptime, rotation execution, or raid
    DPS until the later temporal/encounter optimization phases supply those inputs.
    """

    def __init__(self, capability_service) -> None:
        self.capability_service = capability_service

    @staticmethod
    def _clean(value: object) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _player_name(cls, build: PlayerBuild) -> str:
        return cls._clean(getattr(build, "Name", "")) or cls._clean(
            getattr(build, "Gamertag", "")
        ) or "Unnamed Player"

    @classmethod
    def _build_name(cls, build: PlayerBuild) -> str:
        return cls._clean(getattr(build, "BuildName", "")) or "Current Build"

    def analyze(
        self,
        builds: Iterable[PlayerBuild],
        *,
        recruit_count: int = 0,
    ) -> TeamOptimizationCanonicalAnalysis:
        selected = tuple(builds)
        summaries: list[TeamBuildCapabilitySummary] = []
        providers: dict[str, list[str]] = {}
        total_gaps = 0
        conditional_sources: set[str] = set()
        total_boundaries = 0

        for build in selected:
            audit = self.capability_service.audit_build(build)
            player_name = self._player_name(build)
            build_name = self._build_name(build)
            effect_names = tuple(
                dict.fromkeys(
                    self._clean(getattr(effect, "name", ""))
                    for effect in audit.resolved_effects
                    if self._clean(getattr(effect, "name", ""))
                )
            )
            gaps = tuple(
                self._clean(value)
                for value in audit.capability_resolution_gaps
                if self._clean(value)
            )
            conditional = tuple(
                self._clean(value)
                for value in audit.conditional_sources
                if self._clean(value)
            )
            boundaries = tuple(
                self._clean(value)
                for value in audit.boundaries
                if self._clean(value)
            )
            summaries.append(
                TeamBuildCapabilitySummary(
                    player_name=player_name,
                    build_name=build_name,
                    resolved_effects=effect_names,
                    capability_gaps=gaps,
                    conditional_sources=conditional,
                    boundaries=boundaries,
                )
            )
            for effect_name in effect_names:
                provider_names = providers.setdefault(effect_name, [])
                if player_name not in provider_names:
                    provider_names.append(player_name)
            total_gaps += len(gaps)
            conditional_sources.update(conditional)
            total_boundaries += len(boundaries)

        provider_rows = tuple(
            (effect_name, tuple(provider_names))
            for effect_name, provider_names in sorted(
                providers.items(), key=lambda item: item[0].casefold()
            )
        )
        return TeamOptimizationCanonicalAnalysis(
            saved_build_count=len(selected),
            recruit_count=max(0, int(recruit_count)),
            build_summaries=tuple(summaries),
            capability_providers=provider_rows,
            capability_gap_count=total_gaps,
            conditional_source_count=len(conditional_sources),
            boundary_count=total_boundaries,
        )
