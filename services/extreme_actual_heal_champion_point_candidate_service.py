from __future__ import annotations

"""Generate legal Champion Point loadout candidates for Extreme actual healing.

Champion Point mechanics remain owned by the canonical CP repository and the
component-scoped healing resolver. This service discovers CP stars that can
change the magnitude of one identified heal, proves Champion Bar legality, and
materializes legal loadouts onto real ``PlayerBuild`` candidates.

Mixed CP units are never ranked here. Flat Weapon/Spell Damage, Max Resource,
Healing Done, and Critical Healing remain incomparable until the canonical heal
evaluator scores the resulting build.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.champion_point_static_repository import (
    EXTERNALLY_MODELED_DYNAMIC_CP_NAMES,
    ChampionPointRecord,
    ChampionPointStaticRepository,
)
from minmax.stat_ids import StatId
from models.build_model import ChampionPointEntry, PlayerBuild
from minmax.build_candidate import BuildCandidate
from services.champion_point_loadout_service import (
    ChampionPointLoadoutService,
    ChampionPointSlotCandidate,
)
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService


_REVIEWED_COMPONENT_HEALING_CP = frozenset(
    {"focused mending", "rejuvenator", "soothing tide", "swift renewal"}
)

# Reviewed dynamic CP whose tooltips mention healing, recovery, shields, or
# Weapon/Spell Damage but do not increase the magnitude of the heal event H1 is
# scoring. They may matter to sustain, support, survivability, proc output, or a
# different event and therefore remain available to those consumers instead.
_REVIEWED_NON_MAGNITUDE_CP = frozenset(
    {
        "cleansing revival",
        "enlivening overflow",
        "foresight",
        "hope infusion",
        "last stand",
        "peace of mind",
        "reaving blows",
        "refreshing stride",
        "salve of renewal",
        "soothing shield",
        "strategic reserve",
        "sustained by suffering",
        "wrathful strikes",
    }
)

_HEAL_RELEVANT_STATS = frozenset(
    {
        StatId.MAX_MAGICKA,
        StatId.MAX_STAMINA,
        StatId.WEAPON_DAMAGE,
        StatId.SPELL_DAMAGE,
        StatId.HEALING_DONE,
        StatId.CRITICAL_HEALING,
    }
)
_HEAL_RELEVANT_DESCRIPTION_MARKERS = (
    "healing done",
    "healing abilities",
    "max magicka",
    "max stamina",
    "critical healing",
)


@dataclass(frozen=True)
class ExtremeActualHealChampionPointCandidateResult:
    candidates: tuple[BuildCandidate, ...] = ()
    relevant_star_names: tuple[str, ...] = ()
    legal_loadout_count: int = 0
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        return not self.unresolved


class ExtremeActualHealChampionPointCandidateService:
    """Materialize every reviewed heal-magnitude-relevant legal CP loadout."""

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        repository: ChampionPointStaticRepository | None = None,
    ) -> None:
        if repository is None:
            if database_path is None:
                raise ValueError("database_path is required when repository is not supplied")
            repository = ChampionPointStaticRepository(database_path)
        self.repository = repository

    @staticmethod
    def _description_may_affect_actual_heal(description: str) -> bool:
        text = " ".join(str(description or "").strip().casefold().split())
        return any(marker in text for marker in _HEAL_RELEVANT_DESCRIPTION_MARKERS)

    def _discover(self) -> tuple[tuple[ChampionPointRecord, ...], tuple[str, ...]]:
        relevant: list[ChampionPointRecord] = []
        unresolved: list[str] = []
        for record in self.repository.slottable_records():
            key = record.name.strip().casefold()
            if key in _REVIEWED_COMPONENT_HEALING_CP:
                relevant.append(record)
                continue
            if key in _REVIEWED_NON_MAGNITUDE_CP:
                continue
            if key in EXTERNALLY_MODELED_DYNAMIC_CP_NAMES:
                # Externally modeled stars outside the reviewed healing-component
                # set belong to another objective/event unless explicitly added.
                continue

            effects, problems = self.repository.resolve(record.name, record.max_points)
            if problems:
                if self._description_may_affect_actual_heal(record.description):
                    unresolved.extend(
                        f"{record.name}: {problem}" for problem in problems
                    )
                continue
            if any(effect.stat in _HEAL_RELEVANT_STATS for effect in effects):
                relevant.append(record)

        ordered = tuple(sorted(relevant, key=lambda row: row.name.casefold()))
        return ordered, tuple(dict.fromkeys(unresolved))

    def build_candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        character_id: str,
        baseline_build_id: str,
    ) -> ExtremeActualHealChampionPointCandidateResult:
        relevant, discovery_unresolved = self._discover()
        slot_candidates = tuple(
            ChampionPointSlotCandidate(
                name=record.name,
                discipline_index=record.discipline_index,
            )
            for record in relevant
        )
        enumeration = ChampionPointLoadoutService.enumerate_legal_loadouts(
            slot_candidates
        )
        unresolved = list(discovery_unresolved)
        unresolved.extend(enumeration.unresolved)
        if unresolved:
            return ExtremeActualHealChampionPointCandidateResult(
                relevant_star_names=tuple(row.name for row in relevant),
                legal_loadout_count=len(enumeration.loadouts),
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        records_by_name = {record.name.casefold(): record for record in relevant}
        impacted_disciplines = {
            int(record.discipline_index)
            for record in relevant
            if record.discipline_index is not None
        }

        preserved: list[ChampionPointEntry] = []
        for entry in baseline_build.ChampionPoints:
            name = str(entry.Name or "").strip()
            if not name:
                continue
            record = self.repository.get(name)
            if record is None:
                unresolved.append(
                    f"Saved Champion Point not found in canonical repository: {name}"
                )
                continue
            discipline = record.discipline_index
            if discipline is None:
                unresolved.append(
                    f"Saved Champion Point has no discipline identity: {name}"
                )
                continue
            if int(discipline) not in impacted_disciplines:
                preserved.append(ChampionPointEntry(Name=name, Points=str(entry.Points or "")))

        if unresolved:
            return ExtremeActualHealChampionPointCandidateResult(
                relevant_star_names=tuple(row.name for row in relevant),
                legal_loadout_count=len(enumeration.loadouts),
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        before = [entry.to_dict() for entry in baseline_build.ChampionPoints]
        before_key = tuple(
            sorted(
                (str(entry.Name or "").strip().casefold(), str(entry.Points or "").strip())
                for entry in baseline_build.ChampionPoints
                if str(entry.Name or "").strip()
            )
        )
        result: list[BuildCandidate] = []
        for index, loadout in enumerate(enumeration.loadouts):
            selected: list[ChampionPointEntry] = []
            for option in loadout:
                record = records_by_name[option.name.casefold()]
                selected.append(
                    ChampionPointEntry(Name=record.name, Points=str(record.max_points))
                )
            after_entries = [*preserved, *selected]
            after_entries.sort(key=lambda entry: str(entry.Name or "").casefold())
            after_key = tuple(
                (str(entry.Name or "").strip().casefold(), str(entry.Points or "").strip())
                for entry in after_entries
            )
            if after_key == before_key:
                continue

            build = PlayerBuild.from_dict(baseline_build.to_dict())
            build.ChampionPoints = [
                ChampionPointEntry(Name=entry.Name, Points=entry.Points)
                for entry in after_entries
            ]
            result.append(
                ExtremeCompleteOptimizationService._direct_candidate(
                    build,
                    character_id=character_id,
                    baseline_build_id=baseline_build_id,
                    token=f"actual-heal-cp-loadout:{index}:" + "+".join(
                        option.name.casefold().replace(" ", "_") for option in loadout
                    ),
                    path="ChampionPoints",
                    before=before,
                    after=[entry.to_dict() for entry in after_entries],
                    source="extreme:actual-heal:champion-point-loadout",
                )
            )

        return ExtremeActualHealChampionPointCandidateResult(
            candidates=tuple(result),
            relevant_star_names=tuple(row.name for row in relevant),
            legal_loadout_count=len(enumeration.loadouts),
        )


__all__ = [
    "ExtremeActualHealChampionPointCandidateResult",
    "ExtremeActualHealChampionPointCandidateService",
]
