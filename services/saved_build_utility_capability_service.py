from __future__ import annotations

"""Project canonical slotted-skill utility semantics into Phase 10 capability evidence.

This is deliberately parallel to the EffectVariant-backed saved-build capability adapter.
Combat utilities such as TAUNT are coefficient-owned structural mechanics, not named
buff/debuff effects, so they should not be forced into EffectVariant just to participate
in provider assignment.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.skill_coefficient_repository import SkillCoefficientRepository
from minmax.skill_component_utility_effect import SkillComponentUtilityEffectType
from minmax.skill_component_utility_effect_repository import (
    SkillComponentUtilityEffectRepository,
)
from models.build_model import PlayerBuild
from services.encounter_requirement_evaluation import (
    CapabilityAssessment,
    RosterCapabilityEvidence,
)


@dataclass(frozen=True)
class SavedBuildUtilityCapabilityMap:
    capability_type: str
    utility_effect_type: SkillComponentUtilityEffectType

    def __post_init__(self) -> None:
        capability_type = str(self.capability_type or "").strip()
        if not capability_type:
            raise ValueError("utility capability_type must be non-empty")
        object.__setattr__(self, "capability_type", capability_type)


DEFAULT_UTILITY_CAPABILITY_MAPS: tuple[SavedBuildUtilityCapabilityMap, ...] = (
    SavedBuildUtilityCapabilityMap(
        capability_type="taunt",
        utility_effect_type=SkillComponentUtilityEffectType.TAUNT,
    ),
)


class SavedBuildUtilityCapabilityService:
    """Resolve exact structural utility capability from saved slotted skills only."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        coefficient_repository: SkillCoefficientRepository | object | None = None,
        utility_repository: SkillComponentUtilityEffectRepository | object | None = None,
        capability_maps: tuple[SavedBuildUtilityCapabilityMap, ...] = DEFAULT_UTILITY_CAPABILITY_MAPS,
    ) -> None:
        self.database_path = Path(database_path)
        self.coefficients = coefficient_repository or SkillCoefficientRepository(self.database_path)
        self.utility = utility_repository or SkillComponentUtilityEffectRepository(self.database_path)
        maps = tuple(capability_maps)
        keys = [entry.capability_type for entry in maps]
        if len(keys) != len(set(keys)):
            raise ValueError("utility capability maps cannot duplicate capability_type")
        self._maps = {entry.capability_type: entry.utility_effect_type for entry in maps}

    @staticmethod
    def _member_id(build: PlayerBuild) -> str:
        member_id = str(
            getattr(build, "CharacterId", "")
            or getattr(build, "Name", "")
            or getattr(build, "BuildName", "")
            or ""
        ).strip()
        if not member_id:
            raise ValueError("saved build has no usable member identity")
        return member_id

    @staticmethod
    def _slotted_skills(build: PlayerBuild) -> tuple[tuple[str, str], ...]:
        rows: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for bar, values in (
            ("front", tuple(getattr(build, "FrontBarSkills", ()) or ())),
            ("back", tuple(getattr(build, "BackBarSkills", ()) or ())),
        ):
            for raw in values:
                name = str(raw or "").strip()
                if not name:
                    continue
                key = (bar, name.casefold())
                if key in seen:
                    continue
                seen.add(key)
                rows.append((bar, name))
        return tuple(rows)

    def evidence_for(
        self,
        *,
        build: PlayerBuild,
        capability_types: tuple[str, ...],
    ) -> tuple[RosterCapabilityEvidence, ...]:
        requested = tuple(str(value or "").strip() for value in capability_types)
        if any(not value for value in requested):
            raise ValueError("utility capability types must be non-empty")
        if len(requested) != len(set(requested)):
            raise ValueError("utility capability types must be unique")

        member_id = self._member_id(build)
        skills = self._slotted_skills(build)
        rows: list[RosterCapabilityEvidence] = []

        for capability_type in requested:
            utility_type = self._maps.get(capability_type)
            if utility_type is None:
                rows.append(
                    RosterCapabilityEvidence(
                        member_id=member_id,
                        capability_type=capability_type,
                        assessment=CapabilityAssessment.UNKNOWN,
                        source="no audited structural utility capability mapping",
                    )
                )
                continue

            providers: list[str] = []
            unresolved: list[str] = []
            for bar, skill_name in skills:
                resolution = self.coefficients.resolve_name(skill_name)
                rank = getattr(resolution, "rank", None)
                if rank is None:
                    messages = tuple(getattr(resolution, "unresolved", ())) or (
                        "canonical skill rank is unresolved",
                    )
                    unresolved.extend(f"{skill_name}: {message}" for message in messages)
                    continue

                matched = False
                for coefficient in tuple(getattr(rank, "coefficients", ())):
                    number = int(getattr(coefficient, "coefficient_number"))
                    effects = tuple(self.utility.resolve(rank.skill_rank_id, number))
                    if any(effect.effect_type is utility_type for effect in effects):
                        matched = True
                        break
                if matched:
                    providers.append(f"{skill_name} ({bar})")

            if providers:
                rows.append(
                    RosterCapabilityEvidence(
                        member_id=member_id,
                        capability_type=capability_type,
                        assessment=CapabilityAssessment.SUPPORTED,
                        source="canonical slotted utility: " + ", ".join(dict.fromkeys(providers)),
                    )
                )
            elif unresolved:
                rows.append(
                    RosterCapabilityEvidence(
                        member_id=member_id,
                        capability_type=capability_type,
                        assessment=CapabilityAssessment.UNKNOWN,
                        source="slotted utility resolution unresolved: " + "; ".join(dict.fromkeys(unresolved)),
                    )
                )
            else:
                rows.append(
                    RosterCapabilityEvidence(
                        member_id=member_id,
                        capability_type=capability_type,
                        assessment=CapabilityAssessment.UNSUPPORTED,
                        source="all slotted skills resolved and no mapped structural utility is present",
                    )
                )

        return tuple(rows)


__all__ = [
    "DEFAULT_UTILITY_CAPABILITY_MAPS",
    "SavedBuildUtilityCapabilityMap",
    "SavedBuildUtilityCapabilityService",
]
