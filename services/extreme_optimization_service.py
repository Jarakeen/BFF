from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from engine.config import get_data_dir
from minmax.build_candidate import BuildCandidate, BuildChange
from minmax.build_candidate_armor_enchant import enumerate_armor_enchant_candidates
from minmax.build_candidate_armor_trait import enumerate_armor_trait_candidates
from minmax.build_candidate_food import enumerate_food_candidates
from minmax.build_candidate_mundus import enumerate_mundus_candidates
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_set_repository import GearSetRepository
from minmax.mundus_repository import MundusRepository
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from minmax.race_repository import RaceRepository
from minmax.stat_ids import StatId
from models.build_model import JEWELRY_TRAITS, WEAPON_TRAITS, PlayerBuild
from services.build_service import BuildService
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter


@dataclass(frozen=True)
class ExtremeObjective:
    key: str
    label: str
    ratio: bool = False


EXTREME_OBJECTIVES: tuple[ExtremeObjective, ...] = (
    ExtremeObjective("max_health", "Maximum Health"),
    ExtremeObjective("max_magicka", "Maximum Magicka"),
    ExtremeObjective("max_stamina", "Maximum Stamina"),
    ExtremeObjective("health_recovery", "Health Recovery"),
    ExtremeObjective("magicka_recovery", "Magicka Recovery"),
    ExtremeObjective("stamina_recovery", "Stamina Recovery"),
    ExtremeObjective("weapon_damage", "Weapon Damage"),
    ExtremeObjective("spell_damage", "Spell Damage"),
    ExtremeObjective("physical_resistance", "Physical Resistance"),
    ExtremeObjective("spell_resistance", "Spell Resistance"),
    ExtremeObjective("physical_penetration", "Physical Penetration"),
    ExtremeObjective("spell_penetration", "Spell Penetration"),
    ExtremeObjective("weapon_critical", "Weapon Critical", ratio=True),
    ExtremeObjective("spell_critical", "Spell Critical", ratio=True),
    ExtremeObjective("critical_damage", "Critical Damage", ratio=True),
    ExtremeObjective("healing_done", "Healing Done", ratio=True),
)

_OBJECTIVE_BY_KEY = {objective.key: objective for objective in EXTREME_OBJECTIVES}
_STAT_ID_BY_OBJECTIVE = {
    "weapon_damage": StatId.WEAPON_DAMAGE,
    "spell_damage": StatId.SPELL_DAMAGE,
    "physical_resistance": StatId.PHYSICAL_RESISTANCE,
    "spell_resistance": StatId.SPELL_RESISTANCE,
    "physical_penetration": StatId.PHYSICAL_PENETRATION,
    "spell_penetration": StatId.SPELL_PENETRATION,
    "weapon_critical": StatId.WEAPON_CRITICAL,
    "spell_critical": StatId.SPELL_CRITICAL,
    "critical_damage": StatId.CRITICAL_DAMAGE,
    "healing_done": StatId.HEALING_DONE,
}
_RESOURCE_ATTRIBUTE_BY_OBJECTIVE = {
    "max_health": (64, 0, 0),
    "max_magicka": (0, 64, 0),
    "max_stamina": (0, 0, 64),
}
_JEWELRY_FIELDS = ("Necklace", "Ring1", "Ring2")
_WEAPON_FIELDS = ("FrontBarWeapon", "FrontBarOffHand", "BackBarWeapon", "BackBarOffHand")


@dataclass(frozen=True)
class ExtremeOptimizationStep:
    path: str
    before: object
    after: object
    value_before: float
    value_after: float

    @property
    def delta(self) -> float:
        return self.value_after - self.value_before


@dataclass(frozen=True)
class ExtremeOptimizationResult:
    objective: ExtremeObjective
    baseline_build: PlayerBuild
    optimized_build: PlayerBuild
    baseline_value: float
    optimized_value: float
    steps: tuple[ExtremeOptimizationStep, ...]
    unresolved: tuple[str, ...]
    search_scope: tuple[str, ...]
    omitted_scope: tuple[str, ...]

    @property
    def delta(self) -> float:
        return self.optimized_value - self.baseline_value


class ExtremeOptimizationService:
    """Deliberately unconstrained single-stat search using BFF static math.

    This is a laboratory, not a raid recommendation. The search is bounded to
    mutation families BFF can currently resolve deterministically. Unrelated
    unresolved gear effects are reported but do not erase a stat value that the
    canonical character-sheet stack can still prove.
    """

    SEARCH_SCOPE = (
        "attribute allocation",
        "Mundus",
        "armor traits",
        "armor enchants",
        "jewelry traits",
        "jewelry enchants",
        "weapon traits",
        "food/drink",
    )
    OMITTED_SCOPE = (
        "gear-set replacement",
        "class change",
        "race change",
        "skill-bar passive/proc search",
        "group-only buffs",
        "runtime conditional stacks/procs",
    )

    def __init__(self, *, database_path: Path | None = None, builds_path: Path | None = None) -> None:
        data_dir = get_data_dir()
        self.database_path = Path(database_path or data_dir / "eso.db")
        self.builds_path = Path(builds_path or data_dir / "builds.json")
        self.build_service = BuildService(self.builds_path)
        self.race_repository = RaceRepository(self.database_path)
        self.gear_set_repository = GearSetRepository(self.database_path)
        self.mundus_repository = MundusRepository(self.database_path)
        self.provisioning_repository = ProvisioningStaticRepository(self.database_path)
        self.context_factory = BuildCalculationContextFactory(
            race_repository=self.race_repository,
            gear_set_repository=self.gear_set_repository,
        )

    def saved_builds(self) -> tuple[PlayerBuild, ...]:
        return tuple(self.build_service.load().Members)

    @staticmethod
    def objective(key: str) -> ExtremeObjective:
        normalized = str(key or "").strip().casefold()
        if normalized not in _OBJECTIVE_BY_KEY:
            raise ValueError(f"Unknown extreme optimization objective: {key!r}")
        return _OBJECTIVE_BY_KEY[normalized]

    def optimize(
        self,
        baseline_build: PlayerBuild,
        objective_key: str,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
    ) -> ExtremeOptimizationResult:
        objective = self.objective(objective_key)
        progression_resolution = MinmaxCharacterProgressionAdapter(
            self.build_service.canonical.catalog_service
        ).resolve(baseline_build)
        if not progression_resolution.resolved:
            raise ValueError("; ".join(progression_resolution.unresolved))

        character_id = progression_resolution.character_id
        progression = progression_resolution.progression
        baseline_build_id = (
            str(getattr(baseline_build, "BuildId", "") or "").strip()
            or str(baseline_build.BuildName or "").strip()
            or "saved-build"
        )

        current = PlayerBuild.from_dict(baseline_build.to_dict())
        baseline_value, baseline_unresolved = self._evaluate(
            current,
            progression=progression,
            character_id=character_id,
            build_id=f"{baseline_build_id}:extreme:baseline",
            objective=objective,
            active_bar=active_bar,
        )
        current_value = baseline_value
        unresolved = list(baseline_unresolved)
        accepted: list[ExtremeOptimizationStep] = []

        for pass_index in range(max(1, int(max_passes))):
            best: tuple[float, str, BuildCandidate] | None = None
            for candidate in self._candidates(
                current,
                objective=objective,
                character_id=character_id,
                baseline_build_id=f"{baseline_build_id}:extreme:{pass_index}",
            ):
                value, candidate_unresolved = self._evaluate(
                    candidate.candidate_build,
                    progression=progression,
                    character_id=character_id,
                    build_id=candidate.candidate_id,
                    objective=objective,
                    active_bar=active_bar,
                )
                unresolved.extend(candidate_unresolved)
                if value <= current_value + 1e-9:
                    continue
                if best is None or value > best[0] + 1e-9 or (
                    abs(value - best[0]) <= 1e-9 and candidate.candidate_id < best[1]
                ):
                    best = (value, candidate.candidate_id, candidate)

            if best is None:
                break

            next_value, _, winner = best
            change = winner.changes[0]
            accepted.append(
                ExtremeOptimizationStep(
                    path=change.path,
                    before=change.before,
                    after=change.after,
                    value_before=current_value,
                    value_after=next_value,
                )
            )
            current = winner.candidate_build
            current_value = next_value

        return ExtremeOptimizationResult(
            objective=objective,
            baseline_build=PlayerBuild.from_dict(baseline_build.to_dict()),
            optimized_build=current,
            baseline_value=baseline_value,
            optimized_value=current_value,
            steps=tuple(accepted),
            unresolved=tuple(dict.fromkeys(message for message in unresolved if message)),
            search_scope=self.SEARCH_SCOPE,
            omitted_scope=self.OMITTED_SCOPE,
        )

    def _evaluate(
        self,
        build: PlayerBuild,
        *,
        progression: CharacterProgression,
        character_id: str,
        build_id: str,
        objective: ExtremeObjective,
        active_bar: str,
    ) -> tuple[float, tuple[str, ...]]:
        candidate_progression = replace(
            progression,
            attributes=AttributeAllocation(
                health=int(build.AttributeHealth or 0),
                magicka=int(build.AttributeMagicka or 0),
                stamina=int(build.AttributeStamina or 0),
            ),
        )
        context = self.context_factory.build(
            character_id=character_id,
            build_id=build_id,
            build=build,
            progression=candidate_progression,
            active_bar=active_bar,
        )
        return self._objective_value(context, objective), tuple(context.unresolved_gear_effects)

    @staticmethod
    def _objective_value(context, objective: ExtremeObjective) -> float:
        state = context.character_state
        resource_values = {
            "max_health": state.max_health,
            "max_magicka": state.max_magicka,
            "max_stamina": state.max_stamina,
            "health_recovery": state.health_recovery,
            "magicka_recovery": state.magicka_recovery,
            "stamina_recovery": state.stamina_recovery,
        }
        if objective.key in resource_values:
            return float(resource_values[objective.key])
        trace = context.core_state.derived.get(_STAT_ID_BY_OBJECTIVE[objective.key])
        if trace is None:
            raise ValueError(f"Canonical core stat is unavailable for {objective.label}")
        return float(trace.final_value)

    def _candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        objective: ExtremeObjective,
        character_id: str,
        baseline_build_id: str,
    ) -> tuple[BuildCandidate, ...]:
        candidates: list[BuildCandidate] = []
        candidates.extend(enumerate_mundus_candidates(
            baseline_build=baseline_build,
            character_id=character_id,
            baseline_build_id=baseline_build_id,
            mundus_repository=self.mundus_repository,
            candidate_source="extreme:mundus",
        ))
        candidates.extend(enumerate_armor_trait_candidates(
            baseline_build=baseline_build,
            character_id=character_id,
            baseline_build_id=baseline_build_id,
            candidate_source="extreme:armor-trait",
        ))
        candidates.extend(enumerate_armor_enchant_candidates(
            baseline_build=baseline_build,
            character_id=character_id,
            baseline_build_id=baseline_build_id,
            candidate_source="extreme:armor-enchant",
        ))
        candidates.extend(enumerate_food_candidates(
            baseline_build=baseline_build,
            character_id=character_id,
            baseline_build_id=baseline_build_id,
            provisioning_repository=self.provisioning_repository,
            candidate_source="extreme:food",
        ))
        candidates.extend(self._attribute_candidates(
            baseline_build,
            objective=objective,
            character_id=character_id,
            baseline_build_id=baseline_build_id,
        ))
        candidates.extend(self._jewelry_candidates(
            baseline_build,
            character_id=character_id,
            baseline_build_id=baseline_build_id,
        ))
        candidates.extend(self._weapon_trait_candidates(
            baseline_build,
            character_id=character_id,
            baseline_build_id=baseline_build_id,
        ))
        return tuple(candidates)

    @staticmethod
    def _attribute_candidates(
        baseline_build: PlayerBuild,
        *,
        objective: ExtremeObjective,
        character_id: str,
        baseline_build_id: str,
    ) -> tuple[BuildCandidate, ...]:
        allocation = _RESOURCE_ATTRIBUTE_BY_OBJECTIVE.get(objective.key)
        if allocation is None:
            return ()
        before = (
            int(baseline_build.AttributeHealth or 0),
            int(baseline_build.AttributeMagicka or 0),
            int(baseline_build.AttributeStamina or 0),
        )
        if before == allocation:
            return ()
        build = PlayerBuild.from_dict(baseline_build.to_dict())
        build.AttributeHealth, build.AttributeMagicka, build.AttributeStamina = allocation
        return (
            ExtremeOptimizationService._direct_candidate(
                build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
                token=f"attributes:{objective.key}",
                path="Attributes",
                before={"health": before[0], "magicka": before[1], "stamina": before[2]},
                after={"health": allocation[0], "magicka": allocation[1], "stamina": allocation[2]},
                source="extreme:attributes",
            ),
        )

    @staticmethod
    def _jewelry_candidates(
        baseline_build: PlayerBuild,
        *,
        character_id: str,
        baseline_build_id: str,
    ) -> tuple[BuildCandidate, ...]:
        result: list[BuildCandidate] = []
        enchants = (
            "Weapon Damage",
            "Spell Damage",
            "Magicka Recovery",
            "Stamina Recovery",
            "Health Recovery",
        )
        for field_name in _JEWELRY_FIELDS:
            slot = getattr(baseline_build, field_name)
            if slot.is_empty:
                continue
            for trait in JEWELRY_TRAITS:
                trait = str(trait or "").strip()
                if not trait or trait.casefold() == str(slot.Trait or "").strip().casefold():
                    continue
                build = PlayerBuild.from_dict(baseline_build.to_dict())
                getattr(build, field_name).Trait = trait
                result.append(ExtremeOptimizationService._direct_candidate(
                    build,
                    character_id=character_id,
                    baseline_build_id=baseline_build_id,
                    token=f"jewelry-trait:{field_name}:{trait}",
                    path=f"{field_name}.Trait",
                    before=slot.Trait,
                    after=trait,
                    source="extreme:jewelry-trait",
                ))
            for enchant in enchants:
                if enchant.casefold() == str(slot.Enchant or "").strip().casefold():
                    continue
                build = PlayerBuild.from_dict(baseline_build.to_dict())
                getattr(build, field_name).Enchant = enchant
                result.append(ExtremeOptimizationService._direct_candidate(
                    build,
                    character_id=character_id,
                    baseline_build_id=baseline_build_id,
                    token=f"jewelry-enchant:{field_name}:{enchant}",
                    path=f"{field_name}.Enchant",
                    before=slot.Enchant,
                    after=enchant,
                    source="extreme:jewelry-enchant",
                ))
        return tuple(result)

    @staticmethod
    def _weapon_trait_candidates(
        baseline_build: PlayerBuild,
        *,
        character_id: str,
        baseline_build_id: str,
    ) -> tuple[BuildCandidate, ...]:
        result: list[BuildCandidate] = []
        for field_name in _WEAPON_FIELDS:
            slot = getattr(baseline_build, field_name)
            if slot.is_empty:
                continue
            for trait in WEAPON_TRAITS:
                trait = str(trait or "").strip()
                if not trait or trait.casefold() == str(slot.Trait or "").strip().casefold():
                    continue
                build = PlayerBuild.from_dict(baseline_build.to_dict())
                getattr(build, field_name).Trait = trait
                result.append(ExtremeOptimizationService._direct_candidate(
                    build,
                    character_id=character_id,
                    baseline_build_id=baseline_build_id,
                    token=f"weapon-trait:{field_name}:{trait}",
                    path=f"{field_name}.Trait",
                    before=slot.Trait,
                    after=trait,
                    source="extreme:weapon-trait",
                ))
        return tuple(result)

    @staticmethod
    def _direct_candidate(
        build: PlayerBuild,
        *,
        character_id: str,
        baseline_build_id: str,
        token: str,
        path: str,
        before: object,
        after: object,
        source: str,
    ) -> BuildCandidate:
        safe = "-".join(str(token).casefold().replace("'", "").split())
        return BuildCandidate.from_build(
            character_id=character_id,
            baseline_build_id=baseline_build_id,
            candidate_id=f"{baseline_build_id}:{safe}",
            candidate_build=build,
            changes=(BuildChange.from_values(
                path=path,
                before=before,
                after=after,
                source=source,
            ),),
            candidate_source=source,
        )


def format_extreme_value(objective: ExtremeObjective, value: float) -> str:
    if objective.ratio:
        return f"{value * 100:.2f}%"
    return f"{value:,.0f}"
