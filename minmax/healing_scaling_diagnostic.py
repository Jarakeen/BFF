from __future__ import annotations

from dataclasses import dataclass

from .skill_coefficients import SkillCoefficient


@dataclass(frozen=True)
class HealingScenario:
    """One deliberately explicit healing-tooltip diagnostic scenario.

    These scenarios are investigative, not production combat rules. They let us
    compare an observed ESO tooltip against combinations of individually sourced
    mechanics without silently promoting an unresolved stacking/visibility rule.
    """

    name: str
    effective_power_flat: float = 0.0
    power_percent: float = 0.0
    tooltip_healing_done: float = 0.0
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class HealingScenarioResult:
    scenario: HealingScenario
    base_power: float
    effective_power: float
    base_coefficient_value: float
    tooltip_value: float


def evaluate_healing_scenario(
    coefficient: SkillCoefficient,
    *,
    max_stat: float,
    base_power: float,
    scenario: HealingScenario,
) -> HealingScenarioResult:
    """Evaluate one type-8 healing scenario with explicit assumptions.

    The diagnostic order is deliberately visible:

      effective_power = (base_power + flat healing-only power) * (1 + power %)
      coefficient_value = A*MaxStat + B*effective_power + C
      tooltip_value = coefficient_value * (1 + additive tooltip Healing Done)

    The ordering is a diagnostic hypothesis. It must not be reused as a general
    ESO stacking rule until independently verified.
    """

    coefficient_type = str(coefficient.type or "").strip()
    if coefficient_type != "8":
        raise ValueError(f"healing scenario diagnostic requires type 8, got {coefficient_type!r}")
    if max_stat < 0 or base_power < 0:
        raise ValueError("max_stat and base_power cannot be negative")

    effective_power = (
        float(base_power) + float(scenario.effective_power_flat)
    ) * (1.0 + float(scenario.power_percent))
    base_value = (
        float(coefficient.a) * float(max_stat)
        + float(coefficient.b) * effective_power
        + float(coefficient.c)
    )
    tooltip_value = base_value * (1.0 + float(scenario.tooltip_healing_done))
    return HealingScenarioResult(
        scenario=scenario,
        base_power=float(base_power),
        effective_power=effective_power,
        base_coefficient_value=base_value,
        tooltip_value=tooltip_value,
    )


def combat_prayer_investigation_scenarios(*, ritual_bonus: float) -> tuple[HealingScenario, ...]:
    """Current investigation ladder for Combat Prayer.

    Current values are sourced independently; tooltip visibility is deliberately
    called out in notes where it is not yet verified for the current game build.
    Powered appears only as an explicitly hypothetical tooltip-visible scenario,
    because historical testing found it affected actual healing but not ability
    tooltip values. That behavior still requires current validation.
    """

    ritual = float(ritual_bonus)
    restoration_master = 0.05
    soothing_tide = 0.10
    rejuvenator = 205.0
    major_sorcery = 0.20
    major_mending = 0.16
    blessed = 0.02
    powered = 0.09

    common = ritual + restoration_master + soothing_tide
    fully_conditional = common + major_mending

    return (
        HealingScenario(
            name="Ritual only",
            tooltip_healing_done=ritual,
            notes=("Ritual tooltip visibility historically verified",),
        ),
        HealingScenario(
            name="Ritual + Restoration Master",
            tooltip_healing_done=ritual + restoration_master,
            notes=("Restoration Master current value +5%; tooltip-visible historically",),
        ),
        HealingScenario(
            name="+ Soothing Tide",
            tooltip_healing_done=common,
            notes=("Soothing Tide current value +10% AoE Healing Done; current tooltip visibility unresolved",),
        ),
        HealingScenario(
            name="+ Rejuvenator",
            effective_power_flat=rejuvenator,
            tooltip_healing_done=common,
            notes=("Rejuvenator current value +205 W/SD to healing abilities; current tooltip behavior unresolved",),
        ),
        HealingScenario(
            name="+ Major Sorcery",
            effective_power_flat=rejuvenator,
            power_percent=major_sorcery,
            tooltip_healing_done=common,
            notes=("Major Sorcery +20% W/SD; conditional on buff being active",),
        ),
        HealingScenario(
            name="+ Major Mending",
            effective_power_flat=rejuvenator,
            power_percent=major_sorcery,
            tooltip_healing_done=fully_conditional,
            notes=("Major Mending +16% Healing Done; conditional on buff being active",),
        ),
        HealingScenario(
            name="+ Blessed",
            effective_power_flat=rejuvenator,
            power_percent=major_sorcery,
            tooltip_healing_done=fully_conditional + blessed,
            notes=("Blessed is a non-slottable Warfare passive: +1% Healing Done per stage, max 2%",),
        ),
        HealingScenario(
            name="+ Powered if tooltip-visible",
            effective_power_flat=rejuvenator,
            power_percent=major_sorcery,
            tooltip_healing_done=fully_conditional + blessed + powered,
            notes=("Powered contributes +9% Healing Done on this two-handed Restoration Staff; tooltip visibility is being tested, not assumed",),
        ),
    )
