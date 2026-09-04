from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from minmax.ability_cost_repository import AbilityCostRepository
from minmax.build_action_cost_modifiers import BuildActionCostModifierResolver
from minmax.build_candidate_comparison import CandidateConstraint, ConstraintStatus
from minmax.build_candidate_damage import measure_modeled_damage_potency
from minmax.build_candidate_healing import measure_modeled_healing_potency
from minmax.build_sustain import evaluate_named_build_sustain
from minmax.build_sustain_relevance import sustain_relevant_context_unresolved
from minmax.context_factory import BuildCalculationContextFactory
from minmax.dd_damage import DDDamageEvent
from minmax.evaluation_context import EvaluationContext
from minmax.evaluation_objective import EvaluationObjective
from minmax.gear_set_repository import GearSetRepository
from minmax.jewelry_cost_modifier_repository import JewelryCostModifierRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.race_repository import RaceRepository
from minmax.resource_costs import ResourceType
from minmax.saved_build_activity import create_saved_bar_activity_plan
from minmax.saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from minmax.skill_component_classification import SkillEffectKind
from models.build_model import PlayerBuild
from services.build_service import BuildService
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter
from services.team_prescription_candidate_source import (
    PrescribedObjectiveMeasurement,
    PrescribedOpenSlotCandidate,
)
from services.team_role_autofill import normalize_team_role


@dataclass(frozen=True)
class SavedBuildPrescriptionEvaluationSettings:
    active_bar: str = "front"
    duration_seconds: float = 20.0
    damage_type: str = "magical"
    target_resistance: float | None = 18200.0


def _player_name(build: PlayerBuild) -> str:
    return (
        str(build.Name or "").strip()
        or str(build.Gamertag or "").strip()
        or "Unnamed Player"
    )


def build_saved_player_prescription_candidates(
    builds: tuple[PlayerBuild, ...] | list[PlayerBuild],
) -> tuple[PrescribedOpenSlotCandidate, ...]:
    """Snapshot real saved builds as open-slot candidates without mutating them."""

    candidates: list[PrescribedOpenSlotCandidate] = []
    for build in builds:
        payload = json.dumps(
            build.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        digest = sha256(payload.encode("utf-8")).hexdigest()[:20]
        candidates.append(
            PrescribedOpenSlotCandidate.from_build(
                candidate_id=f"saved:{digest}",
                candidate_build=build,
                candidate_source="saved-build-roster",
                player_name=_player_name(build),
            )
        )
    return tuple(candidates)


class SavedBuildPrescriptionObjectiveEvaluator:
    """Resolve saved healer/DD candidates through existing canonical engines.

    DD ranking uses the same explicit standardized single-event metric used by the
    Phase 12 DD audit. Healer ranking uses the verified one-application healing
    component potency metric. Both retain Phase 4 synthetic saved-bar sustain as a
    hard gate. Tank ranking remains unresolved because no authoritative scalar tank
    objective exists yet.
    """

    def __init__(
        self,
        *,
        build_service: BuildService,
        database_path: Path,
        settings: SavedBuildPrescriptionEvaluationSettings = SavedBuildPrescriptionEvaluationSettings(),
    ) -> None:
        self.build_service = build_service
        self.database_path = Path(database_path)
        self.settings = settings
        self.progression = MinmaxCharacterProgressionAdapter(
            build_service.canonical.catalog_service
        )
        self.context_factory = BuildCalculationContextFactory(
            race_repository=RaceRepository(self.database_path),
            gear_set_repository=GearSetRepository(self.database_path),
        )
        self.tooltip_service = SavedBuildSkillTooltipService(self.database_path)
        self.ability_cost_repository = AbilityCostRepository(self.database_path)
        self.cost_modifier_resolver = BuildActionCostModifierResolver(
            JewelryCostModifierRepository(self.database_path),
            JewelryTraitRepository(self.database_path),
        )

    def __call__(
        self,
        candidate: PrescribedOpenSlotCandidate,
        slot_name: str,
    ) -> PrescribedObjectiveMeasurement:
        build = candidate.candidate_build
        role = normalize_team_role(build.Role)
        if role == "dd":
            return self._evaluate_dd(candidate, slot_name)
        if role == "healer":
            return self._evaluate_healer(candidate, slot_name)
        return PrescribedObjectiveMeasurement(
            objective=EvaluationObjective.SURVIVABILITY,
            value=None,
            metric_name="authoritative tank objective unavailable",
            constraints=(),
            unresolved=(
                f"{slot_name}: BFF has no authoritative scalar tank ranking objective yet; "
                "tank selection remains explicit rather than guessed",
            ),
        )

    def _context(self, candidate: PrescribedOpenSlotCandidate):
        build = candidate.candidate_build
        progression = self.progression.resolve(build)
        if not progression.resolved:
            return None, tuple(progression.unresolved)
        context = self.context_factory.build(
            character_id=progression.character_id,
            build_id=candidate.candidate_id,
            build=build,
            progression=progression.progression,
            active_bar=self.settings.active_bar,
            fight_duration=self.settings.duration_seconds,
            target_resistance=self.settings.target_resistance,
        )
        return context, tuple(context.unresolved_gear_effects)

    def _sustain_constraints(
        self,
        build: PlayerBuild,
        context,
        context_unresolved: tuple[str, ...],
    ) -> tuple[tuple[CandidateConstraint, ...], tuple[str, ...]]:
        relevant_context_unresolved = sustain_relevant_context_unresolved(
            build,
            context_unresolved,
        )
        if relevant_context_unresolved:
            explanation = "Sustain context is unresolved: " + "; ".join(
                relevant_context_unresolved
            )
            return (
                tuple(
                    CandidateConstraint(
                        name=f"{resource.value} sustain",
                        status=ConstraintStatus.UNKNOWN,
                        explanation=explanation,
                    )
                    for resource in (ResourceType.MAGICKA, ResourceType.STAMINA)
                ),
                relevant_context_unresolved,
            )

        plan = create_saved_bar_activity_plan(
            build,
            active_bar=self.settings.active_bar,
            duration_seconds=self.settings.duration_seconds,
        )
        constraints: list[CandidateConstraint] = []
        unresolved: list[str] = []
        for resource in (ResourceType.MAGICKA, ResourceType.STAMINA):
            run = evaluate_named_build_sustain(
                build=build,
                context=context,
                resource=resource,
                duration_seconds=self.settings.duration_seconds,
                actions=plan.actions,
                ability_cost_repository=self.ability_cost_repository,
                cost_modifier_resolver=self.cost_modifier_resolver,
            )
            if run.unresolved:
                messages = tuple(dict.fromkeys(str(value) for value in run.unresolved))
                unresolved.extend(messages)
                constraints.append(
                    CandidateConstraint(
                        name=f"{resource.value} sustain",
                        status=ConstraintStatus.UNKNOWN,
                        explanation="Sustain evidence is unresolved: " + "; ".join(messages),
                    )
                )
                continue
            if not run.action_cost_events:
                continue
            constraints.append(
                CandidateConstraint(
                    name=f"{resource.value} sustain",
                    status=(
                        ConstraintStatus.PRESERVED
                        if run.sustain.sustains
                        else ConstraintStatus.UNSATISFIED
                    ),
                    explanation=(
                        f"Synthetic saved-bar stress plan sustains {resource.value}."
                        if run.sustain.sustains
                        else f"Synthetic saved-bar stress plan runs out of {resource.value}."
                    ),
                )
            )
        return tuple(constraints), tuple(dict.fromkeys(unresolved))

    def _active_bar_skills(self, build: PlayerBuild) -> tuple[str, ...]:
        values = (
            build.FrontBarSkills
            if self.settings.active_bar.casefold() == "front"
            else build.BackBarSkills
        )
        return tuple(str(value or "").strip() for value in values if str(value or "").strip())

    def _verified_healing_skills(
        self,
        build: PlayerBuild,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        selected: list[str] = []
        unresolved: list[str] = []
        for skill_name in self._active_bar_skills(build):
            resolution = self.tooltip_service.coefficients.resolve_name(skill_name)
            if resolution.rank is None:
                messages = resolution.unresolved or ("skill identity unresolved",)
                unresolved.extend(f"{skill_name}: {message}" for message in messages)
                continue
            components = self.tooltip_service.components.get_for_skill_rank(
                resolution.rank.skill_rank_id
            )
            if not components:
                unresolved.append(f"{skill_name}: component classification unavailable")
                continue
            if any(component.effect_kind is SkillEffectKind.HEAL for component in components):
                selected.append(skill_name)
            elif any(component.effect_kind is SkillEffectKind.UNKNOWN for component in components):
                unresolved.append(
                    f"{skill_name}: effect kind unresolved for one or more components"
                )
        return tuple(selected), tuple(dict.fromkeys(unresolved))

    def _evaluate_dd(
        self,
        candidate: PrescribedOpenSlotCandidate,
        slot_name: str,
    ) -> PrescribedObjectiveMeasurement:
        build = candidate.candidate_build
        context, context_unresolved = self._context(candidate)
        if context is None:
            return PrescribedObjectiveMeasurement(
                objective=EvaluationObjective.DAMAGE,
                value=None,
                metric_name="canonical single-event expected damage",
                constraints=(),
                unresolved=context_unresolved,
            )
        sustain_constraints, sustain_unresolved = self._sustain_constraints(
            build,
            context,
            context_unresolved,
        )
        event = DDDamageEvent(
            base_value=1000.0,
            scaling_coefficient=1.0,
            damage_type=self.settings.damage_type,
        )
        damage = measure_modeled_damage_potency(
            context=context,
            event=event,
            evaluation_context=EvaluationContext(
                fight_duration=self.settings.duration_seconds,
                target_resistance=self.settings.target_resistance,
            ),
        )
        unresolved = tuple(
            dict.fromkeys((*damage.unresolved, *sustain_unresolved))
        )
        evidence = tuple(damage.evidence) + (
            f"slot={slot_name}",
            f"damage profile={self.settings.damage_type}",
            f"target resistance={self.settings.target_resistance}",
            "boundary=standardized comparison event; not rotation DPS",
        )
        return PrescribedObjectiveMeasurement(
            objective=EvaluationObjective.DAMAGE,
            value=damage.value if damage.resolved else None,
            metric_name=damage.metric_name,
            constraints=sustain_constraints,
            evidence=evidence,
            unresolved=unresolved,
        )

    def _evaluate_healer(
        self,
        candidate: PrescribedOpenSlotCandidate,
        slot_name: str,
    ) -> PrescribedObjectiveMeasurement:
        build = candidate.candidate_build
        context, context_unresolved = self._context(candidate)
        if context is None:
            return PrescribedObjectiveMeasurement(
                objective=EvaluationObjective.HEALING,
                value=None,
                metric_name="modeled healing-component potency",
                constraints=(),
                unresolved=context_unresolved,
            )
        healing_skills, selection_unresolved = self._verified_healing_skills(build)
        healing = measure_modeled_healing_potency(
            build=build,
            context=context,
            skill_names=healing_skills,
            tooltip_service=self.tooltip_service,
        )
        sustain_constraints, sustain_unresolved = self._sustain_constraints(
            build,
            context,
            context_unresolved,
        )
        unresolved = tuple(
            dict.fromkeys(
                (*selection_unresolved, *healing.unresolved, *sustain_unresolved)
            )
        )
        evidence = tuple(healing.evidence) + (
            f"slot={slot_name}",
            "boundary=one application per verified heal component; not HPS",
        )
        return PrescribedObjectiveMeasurement(
            objective=EvaluationObjective.HEALING,
            value=healing.value if healing.resolved else None,
            metric_name="modeled healing-component potency",
            constraints=sustain_constraints,
            evidence=evidence,
            unresolved=unresolved,
        )
