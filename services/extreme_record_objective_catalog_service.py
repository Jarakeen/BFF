from __future__ import annotations

"""Canonical objective catalog for Extreme Records.

Extreme Records asks a deliberately silly but mechanically useful question:
what is the largest legal value ESO permits for one clearly defined objective?
The answers are reusable mechanical boundaries.  Extreme owns the exhaustive
search/proof; consumers such as Comp Maker may consume records but must not
re-implement the underlying ESO mechanics.

This catalog is intentionally broader than ``EXTREME_OBJECTIVES`` in
``extreme_optimization_service``.  That older tuple describes objectives the
current static optimizer can execute today.  This module describes the stable
record vocabulary we are building toward, including event, snapshot, capped,
and sustained/runtime objectives.
"""

from dataclasses import dataclass
from enum import Enum


class ExtremeRecordDomain(str, Enum):
    RESOURCE = "resource"
    OFFENSE = "offense"
    DEFENSE = "defense"
    HEALING = "healing"
    SUSTAIN = "sustain"
    MOVEMENT = "movement"
    STEALTH = "stealth"
    UTILITY = "utility"


class ExtremeRecordMeasure(str, Enum):
    SNAPSHOT = "snapshot"
    EVENT = "event"
    RATIO = "ratio"
    RATING = "rating"
    DURATION = "duration"
    SUSTAINED = "sustained"


@dataclass(frozen=True)
class ExtremeRecordObjective:
    key: str
    label: str
    domain: ExtremeRecordDomain
    measure: ExtremeRecordMeasure
    description: str
    report_effective_cap: bool = False
    runtime_required: bool = False


EXTREME_RECORD_OBJECTIVES: tuple[ExtremeRecordObjective, ...] = (
    ExtremeRecordObjective("actual_heal", "MOST Actual Heal", ExtremeRecordDomain.HEALING, ExtremeRecordMeasure.EVENT, "Largest legal single healing event.", runtime_required=True),
    ExtremeRecordObjective("critical_heal", "MOST Critical Heal", ExtremeRecordDomain.HEALING, ExtremeRecordMeasure.EVENT, "Largest legal single critical healing event.", runtime_required=True),
    ExtremeRecordObjective("healing_done", "MOST Healing %", ExtremeRecordDomain.HEALING, ExtremeRecordMeasure.RATIO, "Highest legal Healing Done snapshot, with applicable conditional amplification reported separately.", runtime_required=True),
    ExtremeRecordObjective("critical_healing", "MOST Critical Healing", ExtremeRecordDomain.HEALING, ExtremeRecordMeasure.RATIO, "Highest legal Critical Healing modifier snapshot.", report_effective_cap=True, runtime_required=True),
    ExtremeRecordObjective("max_health", "MOST Health", ExtremeRecordDomain.RESOURCE, ExtremeRecordMeasure.SNAPSHOT, "Highest legal Max Health."),
    ExtremeRecordObjective("max_magicka", "MOST Magicka", ExtremeRecordDomain.RESOURCE, ExtremeRecordMeasure.SNAPSHOT, "Highest legal Max Magicka."),
    ExtremeRecordObjective("max_stamina", "MOST Stamina", ExtremeRecordDomain.RESOURCE, ExtremeRecordMeasure.SNAPSHOT, "Highest legal Max Stamina."),
    ExtremeRecordObjective("weapon_damage", "MOST Weapon Damage", ExtremeRecordDomain.OFFENSE, ExtremeRecordMeasure.SNAPSHOT, "Highest legal Weapon Damage snapshot.", runtime_required=True),
    ExtremeRecordObjective("spell_damage", "MOST Spell Damage", ExtremeRecordDomain.OFFENSE, ExtremeRecordMeasure.SNAPSHOT, "Highest legal Spell Damage snapshot.", runtime_required=True),
    ExtremeRecordObjective("weapon_critical", "MOST Weapon Critical Rating", ExtremeRecordDomain.OFFENSE, ExtremeRecordMeasure.RATING, "Highest legal Weapon Critical rating, with resulting chance reported."),
    ExtremeRecordObjective("spell_critical", "MOST Spell Critical Rating", ExtremeRecordDomain.OFFENSE, ExtremeRecordMeasure.RATING, "Highest legal Spell Critical rating, with resulting chance reported."),
    ExtremeRecordObjective("critical_damage", "MOST Critical Damage", ExtremeRecordDomain.OFFENSE, ExtremeRecordMeasure.RATIO, "Highest legal Critical Damage modifier.", report_effective_cap=True, runtime_required=True),
    ExtremeRecordObjective("physical_penetration", "MOST Physical Penetration", ExtremeRecordDomain.OFFENSE, ExtremeRecordMeasure.SNAPSHOT, "Highest legal Physical Penetration snapshot.", report_effective_cap=True, runtime_required=True),
    ExtremeRecordObjective("spell_penetration", "MOST Spell Penetration", ExtremeRecordDomain.OFFENSE, ExtremeRecordMeasure.SNAPSHOT, "Highest legal Spell Penetration snapshot.", report_effective_cap=True, runtime_required=True),
    ExtremeRecordObjective("physical_resistance", "MOST Physical Resistance", ExtremeRecordDomain.DEFENSE, ExtremeRecordMeasure.SNAPSHOT, "Highest legal raw Physical Resistance, with effective combat cap/value reported separately.", report_effective_cap=True, runtime_required=True),
    ExtremeRecordObjective("spell_resistance", "MOST Spell Resistance", ExtremeRecordDomain.DEFENSE, ExtremeRecordMeasure.SNAPSHOT, "Highest legal raw Spell Resistance, with effective combat cap/value reported separately.", report_effective_cap=True, runtime_required=True),
    ExtremeRecordObjective("damage_shield", "MOST Damage Shield", ExtremeRecordDomain.DEFENSE, ExtremeRecordMeasure.EVENT, "Largest legal single damage-shield application.", report_effective_cap=True, runtime_required=True),
    ExtremeRecordObjective("block_mitigation", "MOST Block Mitigation", ExtremeRecordDomain.DEFENSE, ExtremeRecordMeasure.RATIO, "Highest legal block mitigation snapshot.", report_effective_cap=True, runtime_required=True),
    ExtremeRecordObjective("block_cost_reduction", "MOST Block Cost Reduction", ExtremeRecordDomain.DEFENSE, ExtremeRecordMeasure.RATIO, "Highest legal block-cost reduction snapshot.", report_effective_cap=True, runtime_required=True),
    ExtremeRecordObjective("bash_damage", "MOST Bash Damage", ExtremeRecordDomain.OFFENSE, ExtremeRecordMeasure.EVENT, "Largest legal single bash damage event.", runtime_required=True),
    ExtremeRecordObjective("health_recovery", "MOST Health Recovery", ExtremeRecordDomain.SUSTAIN, ExtremeRecordMeasure.RATING, "Highest legal Health Recovery snapshot.", runtime_required=True),
    ExtremeRecordObjective("magicka_recovery", "MOST Magicka Recovery", ExtremeRecordDomain.SUSTAIN, ExtremeRecordMeasure.RATING, "Highest legal Magicka Recovery snapshot.", runtime_required=True),
    ExtremeRecordObjective("stamina_recovery", "MOST Stamina Recovery", ExtremeRecordDomain.SUSTAIN, ExtremeRecordMeasure.RATING, "Highest legal Stamina Recovery snapshot.", runtime_required=True),
    ExtremeRecordObjective("resource_sustain", "MOST Resource Sustain", ExtremeRecordDomain.SUSTAIN, ExtremeRecordMeasure.SUSTAINED, "Highest legal net resource sustain over an explicit time window.", runtime_required=True),
    ExtremeRecordObjective("ultimate_generation", "MOST Ultimate Generation", ExtremeRecordDomain.UTILITY, ExtremeRecordMeasure.SUSTAINED, "Highest legal Ultimate generation over an explicit time window.", runtime_required=True),
    ExtremeRecordObjective("movement_speed", "MOST Movement Speed", ExtremeRecordDomain.MOVEMENT, ExtremeRecordMeasure.RATIO, "Highest legal raw movement-speed snapshot, with effective cap reported separately.", report_effective_cap=True, runtime_required=True),
    ExtremeRecordObjective("sprint_speed", "MOST Sprint Speed", ExtremeRecordDomain.MOVEMENT, ExtremeRecordMeasure.RATIO, "Highest legal sprint movement-speed snapshot, with effective cap reported separately.", report_effective_cap=True, runtime_required=True),
    ExtremeRecordObjective("stealthed_movement_speed", "MOST Stealthed Movement Speed", ExtremeRecordDomain.MOVEMENT, ExtremeRecordMeasure.RATIO, "Highest legal movement speed while stealthed, with effective cap reported separately.", report_effective_cap=True, runtime_required=True),
    ExtremeRecordObjective("detection_radius_reduction", "MOST Stealthy", ExtremeRecordDomain.STEALTH, ExtremeRecordMeasure.SNAPSHOT, "Smallest legal detection radius / greatest legal detection-radius reduction.", report_effective_cap=True, runtime_required=True),
    ExtremeRecordObjective("invisibility_duration", "MOST Invisible", ExtremeRecordDomain.STEALTH, ExtremeRecordMeasure.DURATION, "Longest legal contiguous invisibility window.", runtime_required=True),
    ExtremeRecordObjective("invisibility_uptime", "MOST Invisibility Uptime", ExtremeRecordDomain.STEALTH, ExtremeRecordMeasure.SUSTAINED, "Highest sustainable invisibility uptime over an explicit time window.", runtime_required=True),
)

_OBJECTIVE_BY_KEY = {objective.key: objective for objective in EXTREME_RECORD_OBJECTIVES}


def get_extreme_record_objective(key: str) -> ExtremeRecordObjective:
    normalized = str(key or "").strip().casefold()
    try:
        return _OBJECTIVE_BY_KEY[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported Extreme Records objective: {key!r}") from exc


def list_extreme_record_objectives(*, domain: ExtremeRecordDomain | str | None = None) -> tuple[ExtremeRecordObjective, ...]:
    if domain is None:
        return EXTREME_RECORD_OBJECTIVES
    try:
        normalized = domain if isinstance(domain, ExtremeRecordDomain) else ExtremeRecordDomain(str(domain).strip().casefold())
    except ValueError as exc:
        raise ValueError(f"Unsupported Extreme Records domain: {domain!r}") from exc
    return tuple(objective for objective in EXTREME_RECORD_OBJECTIVES if objective.domain is normalized)
