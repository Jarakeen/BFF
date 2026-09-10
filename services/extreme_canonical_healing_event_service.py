from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from engine.config import get_data_dir
from minmax.saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from minmax.skill_component_classification import HealRecipientScope
from services.extreme_dragon_blood_skill_component_repository import (
    ExtremeDragonBloodSkillComponentRepository,
)
from services.extreme_healing_event_group_scoring_service import (
    ExtremeHealingEventGroupScoringService,
)
from services.extreme_healing_event_recipient_scope_service import (
    ExtremeHealingEventRecipientScopeService,
    ExtremeHealingEventRecipientScopeResult,
)
from services.extreme_healing_event_service import (
    ExtremeHealingEventResult,
    ExtremeHealingEventService,
)
from services.extreme_healing_event_temporal_scope_service import (
    ExtremeHealingEventTemporalScopeResult,
    ExtremeHealingEventTemporalScopeService,
)
from services.extreme_sorcerer_skill_component_repository import (
    ExtremeSorcererSkillComponentRepository,
)
from services.rotation_healer_u50_skill_component_repository import (
    RotationHealerU50SkillComponentRepository,
)


class _CanonicalIdentityRecipientScope:
    """Let canonical component identity own recipient separation during base math."""

    def resolve(
        self,
        *,
        ability_name: str,
        heal_coefficient_numbers: tuple[int, ...] = (),
        coefficient_traces: tuple[object, ...] = (),
    ) -> ExtremeHealingEventRecipientScopeResult:
        _ = (ability_name, heal_coefficient_numbers, coefficient_traces)
        return ExtremeHealingEventRecipientScopeResult(
            single_recipient_safe=True,
            recipient_selection_required=False,
            unresolved=(),
        )


class _CanonicalIdentityTemporalScope:
    """Let canonical component identity own event-time separation during base math."""

    def resolve(self, *, ability_name: str) -> ExtremeHealingEventTemporalScopeResult:
        return ExtremeHealingEventTemporalScopeResult(
            single_instant_safe=True,
            component_time_selection_required=False,
            unresolved=(),
        )


class ExtremeCanonicalHealingEventService(ExtremeHealingEventService):
    """Score proven one-recipient, one-time HEAL events independently.

    The mature ``ExtremeHealingEventService`` remains authoritative for coefficient
    math, Healing Done, family/situational modifiers, Critical Healing, class
    passives, and the critical-healing cap. This adapter changes only the final
    event aggregation boundary.

    When every HEAL coefficient has reviewed recipient and event identity, the
    adapter reconstructs the already-calculated per-coefficient values and lets
    ``ExtremeHealingEventGroupScoringService`` select the largest legitimate
    player-recipient event. Coefficients delivered to another recipient or at
    another time are not added together, and PET-only groups are outside this
    objective rather than allowed to win it.

    The default tooltip path layers reviewed U50 Dragon Blood-family, Sorcerer,
    and common healer component identity in memory. The persistent ``eso.db``
    remains untouched. The existing reviewed ability-name recipient/time guards
    remain a compatibility fallback for skills whose canonical component identity
    has not yet been enriched or whose periodic tick identity is still unresolved.

    A reviewed ``pet_special_activation`` identity proves what the heal does when
    the special can be activated; it does not prove the corresponding Sorcerer pet
    is actually summoned and alive at runtime. Until a canonical runtime pet-state
    input exists, those events retain their numeric lower-bound score but carry an
    explicit unresolved legality blocker and therefore cannot be mechanically
    complete.

    Dragon Blood-family coefficient identity likewise proves which recipient/event
    is being scored, but the U50 family also has missing-Health-dependent healing
    behavior that is not yet represented at per-component scope. Those candidates
    retain their currently calculable coefficient value as a lower bound and carry
    a specific unresolved blocker so the optimizer cannot mistake that lower bound
    for a proved maximum event.
    """

    PLAYER_RECIPIENT_SCOPES = (
        HealRecipientScope.SELF,
        HealRecipientScope.ALLY,
        HealRecipientScope.SELF_OR_ALLY,
        HealRecipientScope.GROUP,
    )
    PET_SPECIAL_ACTIVATION_UNRESOLVED = (
        "Sorcerer pet special activation requires runtime proof that the corresponding pet is summoned and alive"
    )
    DRAGON_BLOOD_WOUND_UNRESOLVED = {
        ExtremeDragonBloodSkillComponentRepository.DRAGON_BLOOD_RANK_ID: (
            "Dragon Blood maximum-event scaling requires explicit caster missing-Health input"
        ),
        ExtremeDragonBloodSkillComponentRepository.GREEN_DRAGON_BLOOD_RANK_ID: (
            "Blood of the Green Dragon maximum-event scaling requires component-specific missing-Health and periodic-tick proof"
        ),
        ExtremeDragonBloodSkillComponentRepository.ELDER_DRAGON_BLOOD_RANK_ID: (
            "Blood of the Elder Dragon maximum-event scaling requires component-specific missing-Health proof for the winning recipient"
        ),
    }

    def __init__(
        self,
        *,
        event_group_scoring: ExtremeHealingEventGroupScoringService | None = None,
        recipient_scope: ExtremeHealingEventRecipientScopeService | None = None,
        temporal_scope: ExtremeHealingEventTemporalScopeService | None = None,
        **kwargs,
    ) -> None:
        self.legacy_recipient_scope = (
            recipient_scope or ExtremeHealingEventRecipientScopeService()
        )
        self.legacy_temporal_scope = (
            temporal_scope or ExtremeHealingEventTemporalScopeService()
        )
        self.event_group_scoring = (
            event_group_scoring or ExtremeHealingEventGroupScoringService()
        )

        if kwargs.get("tooltip_service") is None:
            database_path = Path(
                kwargs.get("database_path") or get_data_dir() / "eso.db"
            )
            dragon_blood_repository = ExtremeDragonBloodSkillComponentRepository(
                database_path
            )
            sorcerer_repository = ExtremeSorcererSkillComponentRepository(
                database_path,
                base_repository=dragon_blood_repository,
            )
            component_repository = RotationHealerU50SkillComponentRepository(
                database_path,
                base_repository=sorcerer_repository,
            )
            kwargs["tooltip_service"] = SavedBuildSkillTooltipService(
                database_path,
                component_repository=component_repository,
            )

        super().__init__(
            recipient_scope=_CanonicalIdentityRecipientScope(),
            temporal_scope=_CanonicalIdentityTemporalScope(),
            **kwargs,
        )

    @staticmethod
    def _component_values(event: ExtremeHealingEventResult) -> dict[int, float]:
        result = event.tooltip_result
        actual_by_number = {
            int(trace.coefficient_number): float(trace.output_value)
            for trace in tuple(getattr(result, "component_actual_effect_trace", ()) or ())
        }
        base_by_number = {
            int(trace.coefficient_number): float(trace.final_value)
            for trace in tuple(getattr(result, "components", ()) or ())
        }
        values: dict[int, float] = {}
        for number in event.heal_coefficient_numbers:
            if number in actual_by_number:
                values[number] = actual_by_number[number]
            elif number in base_by_number:
                values[number] = base_by_number[number]

        if not values or event.normal_heal is None:
            return values

        base_total = sum(float(value) for value in values.values())
        if abs(base_total) <= 1e-12:
            return values
        multiplier = float(event.normal_heal) / base_total
        return {
            number: float(value) * multiplier
            for number, value in values.items()
        }

    def _legacy_scope_fallback(
        self,
        *,
        event: ExtremeHealingEventResult,
        ability_name: str,
    ) -> ExtremeHealingEventResult:
        recipient = self.legacy_recipient_scope.resolve(ability_name=ability_name)
        temporal = self.legacy_temporal_scope.resolve(ability_name=ability_name)
        unresolved = tuple(
            dict.fromkeys(
                message
                for message in (
                    *event.unresolved,
                    *recipient.unresolved,
                    *temporal.unresolved,
                )
                if message
            )
        )
        if recipient.single_recipient_safe and temporal.single_instant_safe:
            return replace(event, unresolved=unresolved)
        return replace(
            event,
            normal_heal=None,
            critical_heal=None,
            unresolved=unresolved,
        )

    @classmethod
    def _winner_runtime_unresolved(cls, *, skill_rank_id: int, components, scoring) -> tuple[str, ...]:
        winner_numbers = tuple(
            getattr(scoring, "critical_winner_coefficients", ())
            or getattr(scoring, "normal_winner_coefficients", ())
            or ()
        )
        if not winner_numbers:
            return ()

        unresolved: list[str] = []
        by_number = {
            int(component.coefficient_number): component
            for component in tuple(components or ())
        }
        for number in winner_numbers:
            component = by_number.get(int(number))
            event_key = str(getattr(component, "heal_event_key", "") or "").strip().casefold()
            if event_key == "pet_special_activation":
                unresolved.append(cls.PET_SPECIAL_ACTIVATION_UNRESOLVED)
                break

        wound_message = cls.DRAGON_BLOOD_WOUND_UNRESOLVED.get(int(skill_rank_id))
        if wound_message:
            unresolved.append(wound_message)

        return tuple(dict.fromkeys(unresolved))

    def evaluate(self, **kwargs) -> ExtremeHealingEventResult:
        event = super().evaluate(**kwargs)
        result = event.tooltip_result
        skill = getattr(result, "skill", None)
        ability_name = str(getattr(skill, "name", "") or "").strip()
        if skill is None:
            return event

        components = tuple(
            self.tooltip_service.components.get_for_skill_rank(skill.skill_rank_id)
        )
        identity = self.event_group_scoring.identity_service.resolve(components)
        if not identity.complete:
            return self._legacy_scope_fallback(
                event=event,
                ability_name=ability_name,
            )
        if not identity.groups:
            return event

        critical_multiplier = event.critical_multiplier
        if critical_multiplier is None:
            return replace(
                event,
                unresolved=tuple(
                    dict.fromkeys(
                        (*event.unresolved, "Canonical event grouping requires Critical Healing multiplier")
                    )
                ),
            )

        scoring = self.event_group_scoring.score(
            components=components,
            value_by_coefficient=self._component_values(event),
            critical_multiplier=float(critical_multiplier),
            allowed_recipient_scopes=self.PLAYER_RECIPIENT_SCOPES,
        )
        unresolved = tuple(
            dict.fromkeys(
                (
                    *event.unresolved,
                    *scoring.unresolved,
                    *self._winner_runtime_unresolved(
                        skill_rank_id=skill.skill_rank_id,
                        components=components,
                        scoring=scoring,
                    ),
                )
            )
        )
        return replace(
            event,
            normal_heal=scoring.largest_normal_heal,
            critical_heal=scoring.largest_critical_heal,
            unresolved=unresolved,
        )
