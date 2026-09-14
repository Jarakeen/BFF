from __future__ import annotations

"""Project canonical slotted-skill utility semantics into Phase 10 capability evidence.

Combat utilities such as TAUNT are coefficient-owned structural mechanics, not named
buff/debuff effects, so they should not be forced into EffectVariant just to participate
in provider assignment.

The service also exposes the exact slotted skill/bar sources that prove a utility. That
structured source boundary exists so downstream rotation policy can reuse canonical
provider evidence without parsing the human-readable ``RosterCapabilityEvidence.source``
string back into mechanics.
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


@dataclass(frozen=True)
class SavedBuildUtilityProviderSource:
    """Exact saved-build skill/bar source proving one structural utility capability."""

    capability_type: str
    skill_name: str
    bar: str

    def __post_init__(self) -> None:
        capability_type = str(self.capability_type or "").strip()
        skill_name = str(self.skill_name or "").strip()
        bar = str(self.bar or "").strip().casefold()
        if not capability_type:
            raise ValueError("utility provider source capability_type must be non-empty")
        if not skill_name:
            raise ValueError("utility provider source skill_name must be non-empty")
        if bar not in {"front", "back"}:
            raise ValueError("utility provider source bar must be front or back")
        object.__setattr__(self, "capability_type", capability_type)
        object.__setattr__(self, "skill_name", skill_name)
        object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class SavedBuildUtilityProviderSourceResolution:
    capability_type: str
    sources: tuple[SavedBuildUtilityProviderSource, ...] = ()
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        capability_type = str(self.capability_type or "").strip()
        if not capability_type:
            raise ValueError("utility provider source resolution requires capability_type")
        object.__setattr__(self, "capability_type", capability_type)
        object.__setattr__(self, "sources", tuple(self.sources))
        object.__setattr__(
            self,
            "unresolved",
            tuple(str(value).strip() for value in self.unresolved if str(value).strip()),
        )


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

    def provider_sources_for(
        self,
        *,
        build: PlayerBuild,
        capability_type: str,
    ) -> SavedBuildUtilityProviderSourceResolution:
        """Return exact skill/bar sources for one structural utility capability.

        UNKNOWN skill identities remain explicit in ``unresolved``. An empty source set
        with no unresolved evidence means every slotted skill resolved and none provides
        the requested utility.
        """

        resolved_capability = str(capability_type or "").strip()
        if not resolved_capability:
            raise ValueError("utility provider source capability_type must be non-empty")
        utility_type = self._maps.get(resolved_capability)
        if utility_type is None:
            return SavedBuildUtilityProviderSourceResolution(
                capability_type=resolved_capability,
                unresolved=("no audited structural utility capability mapping",),
            )

        providers: list[SavedBuildUtilityProviderSource] = []
        unresolved: list[str] = []
        for bar, skill_name in self._slotted_skills(build):
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
                providers.append(
                    SavedBuildUtilityProviderSource(
                        capability_type=resolved_capability,
                        skill_name=skill_name,
                        bar=bar,
                    )
                )

        unique: list[SavedBuildUtilityProviderSource] = []
        seen: set[tuple[str, str]] = set()
        for source in providers:
            key = (source.bar, source.skill_name.casefold())
            if key in seen:
                continue
            seen.add(key)
            unique.append(source)
        return SavedBuildUtilityProviderSourceResolution(
            capability_type=resolved_capability,
            sources=tuple(unique),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

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
        rows: list[RosterCapabilityEvidence] = []

        for capability_type in requested:
            resolution = self.provider_sources_for(
                build=build,
                capability_type=capability_type,
            )
            if resolution.sources:
                providers = tuple(
                    f"{source.skill_name} ({source.bar})" for source in resolution.sources
                )
                rows.append(
                    RosterCapabilityEvidence(
                        member_id=member_id,
                        capability_type=capability_type,
                        assessment=CapabilityAssessment.SUPPORTED,
                        source="canonical slotted utility: " + ", ".join(providers),
                    )
                )
            elif resolution.unresolved:
                prefix = (
                    "no audited structural utility capability mapping"
                    if resolution.unresolved
                    == ("no audited structural utility capability mapping",)
                    else "slotted utility resolution unresolved: "
                    + "; ".join(resolution.unresolved)
                )
                rows.append(
                    RosterCapabilityEvidence(
                        member_id=member_id,
                        capability_type=capability_type,
                        assessment=CapabilityAssessment.UNKNOWN,
                        source=prefix,
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
    "SavedBuildUtilityProviderSource",
    "SavedBuildUtilityProviderSourceResolution",
]
