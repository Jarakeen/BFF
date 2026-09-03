from __future__ import annotations

from dataclasses import dataclass

from models.build_model import PlayerBuild

from .build_calculation_context import BuildCalculationContext
from .saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from .skill_component_classification import SkillEffectKind


@dataclass(frozen=True)
class ModeledHealingPotency:
    """One-application sum of verified healing coefficient components.

    This is deliberately not HPS. It measures the modeled actual-effect value
    of each verified healing component once for the selected skills. Rotation,
    cast frequency, targets, overheal, encounter uptime, and critical expected
    value remain outside this metric until those semantics are explicitly
    integrated.
    """

    value: float | None
    evaluated_skills: tuple[str, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.value is not None and not self.unresolved


def _unique_skill_names(skill_names: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in skill_names:
        name = str(value or "").strip()
        key = name.casefold()
        if not name or key in seen:
            continue
        seen.add(key)
        result.append(name)
    return tuple(result)


def measure_modeled_healing_potency(
    *,
    build: PlayerBuild,
    context: BuildCalculationContext,
    skill_names: tuple[str, ...],
    tooltip_service: SavedBuildSkillTooltipService,
) -> ModeledHealingPotency:
    """Evaluate verified healing components through the Phase 3 saved-build path."""

    selected = _unique_skill_names(skill_names)
    unresolved: list[str] = []
    evidence: list[str] = []
    evaluated_skills: list[str] = []
    total = 0.0
    healing_components = 0

    for skill_name in selected:
        name_resolution = tooltip_service.coefficients.resolve_name(skill_name)
        if name_resolution.rank is None:
            messages = name_resolution.unresolved or ("skill name could not be resolved",)
            unresolved.extend(f"{skill_name}: {message}" for message in messages)
            continue

        entity_id = name_resolution.rank.entity_id
        result = tooltip_service.evaluate_entity_id(
            build=build,
            context=context,
            entity_id=entity_id,
        )
        if result.unresolved:
            unresolved.extend(f"{skill_name}: {message}" for message in result.unresolved)

        if result.skill is None:
            if not result.unresolved:
                unresolved.append(f"{skill_name}: tooltip evaluation returned no resolved skill")
            continue

        classifications = {
            int(component.coefficient_number): component
            for component in tooltip_service.components.get_for_skill_rank(
                result.skill.skill_rank_id
            )
        }
        actual_by_number = {
            int(trace.coefficient_number): float(trace.output_value)
            for trace in result.component_actual_effect_trace
        }
        evaluated_skills.append(result.skill.name or skill_name)

        for component_trace in result.components:
            number = int(component_trace.coefficient_number)
            classification = classifications.get(number)
            if classification is None:
                unresolved.append(
                    f"{skill_name}: component classification unavailable for coefficient {number}"
                )
                continue
            if classification.effect_kind is SkillEffectKind.UNKNOWN:
                unresolved.append(
                    f"{skill_name}: effect kind unresolved for coefficient {number}"
                )
                continue
            if classification.effect_kind is not SkillEffectKind.HEAL:
                continue

            value = actual_by_number.get(number, float(component_trace.final_value))
            total += value
            healing_components += 1
            evidence.append(
                f"{result.skill.entity_id}: coefficient {number}: modeled heal {value:.6f}"
            )

    if not selected:
        unresolved.append("No skills were selected for modeled healing potency")
    elif healing_components == 0:
        unresolved.append("No verified healing coefficient components were evaluable")

    return ModeledHealingPotency(
        value=total if healing_components else None,
        evaluated_skills=tuple(evaluated_skills),
        evidence=tuple(evidence),
        unresolved=tuple(dict.fromkeys(unresolved)),
    )
