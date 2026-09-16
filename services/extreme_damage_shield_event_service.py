from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minmax.build_calculation_context import BuildCalculationContext
from minmax.formulas.final_calculations import calculate_damage_shield
from minmax.saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from minmax.skill_component_classification import SkillEffectKind
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeDamageShieldModifierInputs:
    cp_damage_shield: float = 0.0
    buff_damage_shield: float = 0.0
    set_damage_shield: float = 0.0
    skill_damage_shield: float = 0.0

    @property
    def combined_bonus(self) -> float:
        return calculate_damage_shield(
            cp_damage_shield=float(self.cp_damage_shield),
            buff_damage_shield=float(self.buff_damage_shield),
            set_damage_shield=float(self.set_damage_shield),
            skill_damage_shield=float(self.skill_damage_shield),
        )


@dataclass(frozen=True)
class ExtremeDamageShieldEventResult:
    entity_id: str
    base_shield: float | None
    modified_shield: float | None
    coefficient_number: int | None
    modifier_bonus: float | None
    unresolved: tuple[str, ...] = ()

    @property
    def mechanic_complete(self) -> bool:
        return self.modified_shield is not None and not self.unresolved


class ExtremeDamageShieldEventService:
    """Evaluate one canonical single damage-shield application.

    Coefficient scaling remains owned by ``SavedBuildSkillTooltipService`` and
    the UESP damage-shield modifier equation remains owned by
    ``calculate_damage_shield``.  This service only selects a proven SHIELD
    component and composes those existing owners into an Extreme event value.

    Until shield recipient/event identity is persisted at component level, a
    skill with more than one SHIELD-classified coefficient fails closed.  It is
    not safe to add multiple shield components together and call that one shield
    application merely because they share an ability name.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        tooltip_service: SavedBuildSkillTooltipService | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.tooltip_service = tooltip_service or SavedBuildSkillTooltipService(
            self.database_path
        )

    def evaluate(
        self,
        *,
        build: PlayerBuild,
        context: BuildCalculationContext,
        entity_id: str,
        modifiers: ExtremeDamageShieldModifierInputs = ExtremeDamageShieldModifierInputs(),
    ) -> ExtremeDamageShieldEventResult:
        normalized_entity = str(entity_id or "").strip()
        if not normalized_entity:
            raise ValueError("Damage-shield entity_id is required")

        tooltip = self.tooltip_service.evaluate_entity_id(
            build=build,
            context=context,
            entity_id=normalized_entity,
        )
        unresolved = list(tuple(getattr(tooltip, "unresolved", ()) or ()))
        skill = getattr(tooltip, "skill", None)
        if skill is None:
            unresolved.append(f"{normalized_entity}: skill rank is unresolved")
            return ExtremeDamageShieldEventResult(
                entity_id=normalized_entity,
                base_shield=None,
                modified_shield=None,
                coefficient_number=None,
                modifier_bonus=None,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        classifications = tuple(
            component
            for component in self.tooltip_service.components.get_for_skill_rank(
                skill.skill_rank_id
            )
            if component.effect_kind is SkillEffectKind.SHIELD
        )
        if not classifications:
            unresolved.append(
                f"{normalized_entity}: no SHIELD-classified coefficient component"
            )
        elif len(classifications) > 1:
            unresolved.append(
                f"{normalized_entity}: multiple SHIELD components require explicit shield-event identity"
            )

        if len(classifications) != 1:
            return ExtremeDamageShieldEventResult(
                entity_id=normalized_entity,
                base_shield=None,
                modified_shield=None,
                coefficient_number=None,
                modifier_bonus=None,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        coefficient_number = int(classifications[0].coefficient_number)
        trace = next(
            (
                component
                for component in tuple(getattr(tooltip, "components", ()) or ())
                if int(component.coefficient_number) == coefficient_number
            ),
            None,
        )
        if trace is None:
            unresolved.append(
                f"{normalized_entity}: SHIELD coefficient {coefficient_number} has no evaluated trace"
            )
            return ExtremeDamageShieldEventResult(
                entity_id=normalized_entity,
                base_shield=None,
                modified_shield=None,
                coefficient_number=coefficient_number,
                modifier_bonus=None,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        base_shield = float(trace.final_value)
        modifier_bonus = float(modifiers.combined_bonus)
        modified_shield = base_shield * (1.0 + modifier_bonus)
        return ExtremeDamageShieldEventResult(
            entity_id=normalized_entity,
            base_shield=base_shield,
            modified_shield=modified_shield,
            coefficient_number=coefficient_number,
            modifier_bonus=modifier_bonus,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeDamageShieldEventResult",
    "ExtremeDamageShieldEventService",
    "ExtremeDamageShieldModifierInputs",
]
