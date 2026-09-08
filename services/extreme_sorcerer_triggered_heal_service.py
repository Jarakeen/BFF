from __future__ import annotations

from dataclasses import dataclass

from minmax.skill_component_classification import HealRecipientScope, HealTemporalScope


@dataclass(frozen=True)
class ExtremeSorcererTriggeredHealResult:
    ability_name: str
    trigger_kind: str
    trigger_satisfied: bool
    recipient_scope: HealRecipientScope
    temporal_scope: HealTemporalScope
    cooldown_seconds: float | None
    normal_heal: float | None
    can_crit: bool | None
    unresolved: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return self.trigger_satisfied and self.normal_heal is not None and not self.unresolved


class ExtremeSorcererTriggeredHealService:
    """Resolve reviewed U50 Sorcerer heals that are not ordinary coefficient rows.

    The canonical U50 ``eso.db`` does not expose normal coefficient rows for the
    Dark Exchange or Surge families. This service therefore owns only reviewed
    trigger/recipient/time semantics. A caller must provide a resolved heal value
    for those families until a trustworthy non-coefficient scaling source exists.

    Blood Magic is the deliberate exception. U50 rank 2 heals the caster for 10%
    of Max Health when a Dark Magic ability with a cost is cast while the caster
    is not at full Health. At full Health, Blood Magic takes its separate resource
    branch instead and emits no healing event.

    Critical eligibility remains unresolved here unless separately proven. A heal
    being *triggered by* a critical event is not evidence that the resulting heal
    itself can critically heal.
    """

    _DARK_EXCHANGE = {"dark exchange", "dark conversion", "dark deal"}
    _SURGE_SELF = {"surge", "critical surge"}
    _POWER_SURGE = "power surge"
    _BLOOD_MAGIC = "blood magic"

    @staticmethod
    def _name(value: str | None) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @staticmethod
    def _resolved_value(
        *,
        ability_name: str,
        resolved_heal_amount: float | None,
    ) -> tuple[float | None, tuple[str, ...]]:
        if resolved_heal_amount is None:
            return None, (
                f"{ability_name} healing value is unresolved because U50 canonical data has no ordinary heal coefficient row",
            )
        value = float(resolved_heal_amount)
        if value < 0:
            raise ValueError("resolved_heal_amount must be non-negative")
        return value, ()

    def resolve(
        self,
        *,
        ability_name: str,
        resolved_heal_amount: float | None = None,
        surge_window_active: bool = False,
        critical_damage_triggered: bool = False,
        critical_heal_triggered: bool = False,
        dark_magic_ability_cast_with_cost: bool = False,
        caster_at_full_health: bool = False,
        max_health: float | None = None,
    ) -> ExtremeSorcererTriggeredHealResult:
        normalized = self._name(ability_name)
        display = str(ability_name or "").strip() or normalized

        if normalized in self._DARK_EXCHANGE:
            value, unresolved = self._resolved_value(
                ability_name=display,
                resolved_heal_amount=resolved_heal_amount,
            )
            return ExtremeSorcererTriggeredHealResult(
                ability_name=display,
                trigger_kind="activation",
                trigger_satisfied=True,
                recipient_scope=HealRecipientScope.SELF,
                temporal_scope=HealTemporalScope.DIRECT,
                cooldown_seconds=None,
                normal_heal=value,
                can_crit=None,
                unresolved=unresolved,
            )

        if normalized in self._SURGE_SELF:
            triggered = bool(surge_window_active and critical_damage_triggered)
            value: float | None = None
            unresolved: tuple[str, ...] = ()
            if triggered:
                value, unresolved = self._resolved_value(
                    ability_name=display,
                    resolved_heal_amount=resolved_heal_amount,
                )
            return ExtremeSorcererTriggeredHealResult(
                ability_name=display,
                trigger_kind="critical_damage_while_surge_active",
                trigger_satisfied=triggered,
                recipient_scope=HealRecipientScope.SELF,
                temporal_scope=HealTemporalScope.DIRECT,
                cooldown_seconds=1.0,
                normal_heal=value,
                can_crit=None,
                unresolved=unresolved,
            )

        if normalized == self._POWER_SURGE:
            triggered = bool(surge_window_active and critical_heal_triggered)
            value = None
            unresolved = ()
            if triggered:
                value, unresolved = self._resolved_value(
                    ability_name=display,
                    resolved_heal_amount=resolved_heal_amount,
                )
            return ExtremeSorcererTriggeredHealResult(
                ability_name=display,
                trigger_kind="critical_heal_while_power_surge_active",
                trigger_satisfied=triggered,
                recipient_scope=HealRecipientScope.GROUP,
                temporal_scope=HealTemporalScope.DIRECT,
                cooldown_seconds=3.0,
                normal_heal=value,
                can_crit=None,
                unresolved=unresolved,
            )

        if normalized == self._BLOOD_MAGIC:
            triggered = bool(
                dark_magic_ability_cast_with_cost and not caster_at_full_health
            )
            if not triggered:
                return ExtremeSorcererTriggeredHealResult(
                    ability_name=display,
                    trigger_kind="dark_magic_costed_cast_below_full_health",
                    trigger_satisfied=False,
                    recipient_scope=HealRecipientScope.SELF,
                    temporal_scope=HealTemporalScope.DIRECT,
                    cooldown_seconds=None,
                    normal_heal=None,
                    can_crit=None,
                    unresolved=(),
                )
            if max_health is None:
                return ExtremeSorcererTriggeredHealResult(
                    ability_name=display,
                    trigger_kind="dark_magic_costed_cast_below_full_health",
                    trigger_satisfied=True,
                    recipient_scope=HealRecipientScope.SELF,
                    temporal_scope=HealTemporalScope.DIRECT,
                    cooldown_seconds=None,
                    normal_heal=None,
                    can_crit=None,
                    unresolved=("Blood Magic U50 rank-2 healing requires Max Health",),
                )
            health = float(max_health)
            if health < 0:
                raise ValueError("max_health must be non-negative")
            return ExtremeSorcererTriggeredHealResult(
                ability_name=display,
                trigger_kind="dark_magic_costed_cast_below_full_health",
                trigger_satisfied=True,
                recipient_scope=HealRecipientScope.SELF,
                temporal_scope=HealTemporalScope.DIRECT,
                cooldown_seconds=None,
                normal_heal=health * 0.10,
                can_crit=None,
                unresolved=(),
            )

        return ExtremeSorcererTriggeredHealResult(
            ability_name=display,
            trigger_kind="unsupported",
            trigger_satisfied=False,
            recipient_scope=HealRecipientScope.SELF,
            temporal_scope=HealTemporalScope.DIRECT,
            cooldown_seconds=None,
            normal_heal=None,
            can_crit=None,
            unresolved=(f"Unsupported Sorcerer triggered-heal source: {display}",),
        )
