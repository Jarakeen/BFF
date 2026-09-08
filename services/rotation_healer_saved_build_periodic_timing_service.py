from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minmax.skill_coefficient_repository import SkillCoefficientRepository
from minmax.skill_component_classification import HealTemporalScope, SkillEffectKind
from minmax.skill_component_repository import SkillComponentRepository
from models.build_model import PlayerBuild
from services.rotation_healer_canonical_periodic_timing_service import (
    RotationHealerCanonicalPeriodicTimingResolution,
    RotationHealerCanonicalPeriodicTimingService,
)
from services.rotation_healer_u50_skill_component_repository import (
    RotationHealerU50SkillComponentRepository,
)


@dataclass(frozen=True)
class RotationHealerSavedBuildPeriodicTimingEntry:
    """One slotted periodic-heal component and its canonical timing evidence."""

    bar: str
    slot: int
    skill_name: str
    coefficient_number: int
    timing: RotationHealerCanonicalPeriodicTimingResolution


@dataclass(frozen=True)
class RotationHealerSavedBuildPeriodicTimingReport:
    character_name: str
    build_name: str
    entries: tuple[RotationHealerSavedBuildPeriodicTimingEntry, ...]
    unresolved: tuple[str, ...] = ()


class RotationHealerSavedBuildPeriodicTimingService:
    """Discover canonical periodic-heal timing for the skills actually slotted.

    This service does not schedule ticks. It joins saved-build bar identity to the
    reviewed U50 component identity overlay and canonical timing resolver so later
    rotation work can operate on the healer's real skills rather than a generic
    catalog. Direct heals, non-healing components, and externally activated
    synergy heals are intentionally ignored.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        coefficient_repository: SkillCoefficientRepository | None = None,
        component_repository: SkillComponentRepository | object | None = None,
        timing_service: RotationHealerCanonicalPeriodicTimingService | None = None,
    ) -> None:
        path = Path(database_path)
        self.coefficients = coefficient_repository or SkillCoefficientRepository(path)
        self.components = component_repository or RotationHealerU50SkillComponentRepository(path)
        self.timing_service = timing_service or RotationHealerCanonicalPeriodicTimingService(path)

    def inspect(self, build: PlayerBuild) -> RotationHealerSavedBuildPeriodicTimingReport:
        entries: list[RotationHealerSavedBuildPeriodicTimingEntry] = []
        unresolved: list[str] = []

        for bar, skills in (
            ("front", tuple(build.FrontBarSkills)),
            ("back", tuple(build.BackBarSkills)),
        ):
            for slot, raw_name in enumerate(skills, start=1):
                skill_name = str(raw_name or "").strip()
                if not skill_name:
                    continue

                resolution = self.coefficients.resolve_name(skill_name)
                if resolution.rank is None:
                    messages = resolution.unresolved or (
                        f"canonical skill identity unresolved for {skill_name}",
                    )
                    unresolved.extend(
                        f"{bar} slot {slot} {skill_name}: {message}" for message in messages
                    )
                    continue

                rank = resolution.rank
                classifications = self.components.get_for_skill_rank(rank.skill_rank_id)
                for component in classifications:
                    if component.effect_kind is not SkillEffectKind.HEAL:
                        continue
                    is_periodic = (
                        component.heal_temporal_scope is HealTemporalScope.PERIODIC
                        or component.is_dot is True
                    )
                    if not is_periodic:
                        continue

                    timing = self.timing_service.resolve(
                        source_name=skill_name,
                        coefficient_number=component.coefficient_number,
                    )
                    entries.append(
                        RotationHealerSavedBuildPeriodicTimingEntry(
                            bar=bar,
                            slot=slot,
                            skill_name=skill_name,
                            coefficient_number=component.coefficient_number,
                            timing=timing,
                        )
                    )
                    unresolved.extend(
                        f"{bar} slot {slot} {skill_name} coefficient {component.coefficient_number}: {message}"
                        for message in timing.unresolved
                    )

        return RotationHealerSavedBuildPeriodicTimingReport(
            character_name=str(build.Name or "").strip(),
            build_name=str(build.BuildName or "").strip(),
            entries=tuple(entries),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
