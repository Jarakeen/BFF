from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from engine.config import get_data_dir
from services.combat_effect_reference_service import (
    CombatEffectReference,
    CombatEffectReferenceService,
)
from services.encounter_projection import EncounterDefinition, EncounterMechanic
from services.encounter_repository import EncounterRepository
from services.gameplay_policy_service import GameplayPolicy, GameplayPolicyService


@dataclass(frozen=True)
class ReferenceEntry:
    name: str
    entry_type: str
    source_scope: str
    tags: tuple[str, ...]
    summary: str
    details: tuple[tuple[str, str], ...]
    related: tuple[str, ...] = ()
    death_note: str = ""
    field_note: str = ""
    used_by: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    @property
    def search_text(self) -> str:
        detail_text = " ".join(f"{key} {value}" for key, value in self.details)
        return " ".join(
            (
                self.name,
                self.entry_type,
                self.source_scope,
                *self.tags,
                self.summary,
                detail_text,
                *self.related,
                self.field_note,
                *self.used_by,
                *self.evidence,
            )
        ).casefold()

    def detail_text(self) -> str:
        return "\n".join(f"{label}: {value}" for label, value in self.details)


_POLICY_PRESENTATION = {
    "standard_light_attack_weave_window": {
        "name": "Light Attack Weaving",
        "entry_type": "Combat Rule",
        "source_scope": "Global Combat",
        "tags": ("WEAVING", "TIMING", "COMBAT RULE"),
        "related": ("Global Cooldown", "Rotation Timeline", "Combat Events"),
        "death_note": (
            "This is normally a rotation-timing rule rather than a direct death cause. "
            "Use Performance / Raid Review to inspect missed or delayed weave events."
        ),
    },
    "dd_redundant_personal_heal": {
        "name": "DD Personal Heal Slot",
        "entry_type": "Role",
        "source_scope": "Player",
        "tags": ("DAMAGE DEALER", "BAR SPACE", "ENDGAME PRACTICE"),
        "related": ("Support Coverage", "Portal Assignment", "Kite / Runner Assignment"),
        "death_note": (
            "A missing personal heal is not automatically a player error. Check whether the "
            "assignment removed reliable healer coverage before blaming the bar."
        ),
    },
    "dd_bar_space_opportunity_cost": {
        "name": "DD Bar-Space Opportunity Cost",
        "entry_type": "Combat Rule",
        "source_scope": "Player",
        "tags": ("DAMAGE DEALER", "SKILL SLOT", "OPTIMIZATION"),
        "related": ("Utility Skill", "Encounter Obligation", "Support DD"),
        "death_note": (
            "This rule explains build tradeoffs, not a specific death. Encounter obligations "
            "can justify spending damage bar space on utility."
        ),
    },
    "healer_support_not_raw_hps": {
        "name": "Healer Support Objective",
        "entry_type": "Role",
        "source_scope": "Player",
        "tags": ("HEALER", "SUPPORT", "ENDGAME PRACTICE"),
        "related": ("Healing Coverage", "Support Uptime", "Sustain Reserve"),
        "death_note": (
            "When reviewing a healer-related death, inspect coverage, mechanic readiness, "
            "positioning and support timing rather than reducing the answer to raw HPS."
        ),
    },
    "healer_assignments_not_interchangeable": {
        "name": "Healer Assignment Specialization",
        "entry_type": "Role",
        "source_scope": "Player",
        "tags": ("HEALER", "ASSIGNMENT", "POSITIONING"),
        "related": ("Group Coverage", "Support Sets", "Encounter Assignment"),
        "death_note": (
            "Compare the death against the healer's actual assignment. Two healer positions "
            "may intentionally have different coverage and responsibilities."
        ),
    },
    "tank_survival_not_only_objective": {
        "name": "Tank Support Objective",
        "entry_type": "Role",
        "source_scope": "Player",
        "tags": ("TANK", "SURVIVAL", "SUPPORT"),
        "related": ("Boss Positioning", "Debuff Coverage", "Encounter Control"),
        "death_note": (
            "Tank review should check survival and encounter control together. Staying alive "
            "while losing positioning, taunt control or required support can still fail the pull."
        ),
    },
    "encounter_assignment_overrides_role_default": {
        "name": "Encounter Assignment Override",
        "entry_type": "Combat Rule",
        "source_scope": "Trial",
        "tags": ("ASSIGNMENT", "ROLE POLICY", "CONTEXT"),
        "related": ("Portal", "Kiting", "Runner Duty", "Group Split"),
        "death_note": (
            "Before applying a generic role expectation to a death, check whether the player's "
            "assignment materially changed support access or survival obligations."
        ),
    },
}


def _title_system(system: str) -> str:
    aliases = {
        "rotation_builder": "Rotation Builder",
        "rotation_timeline": "Rotation Timeline",
        "combat_event_projection": "Combat Event Projection",
        "damage_projection": "Damage Projection",
        "proc_trigger_resolution": "Proc Trigger Resolution",
        "performance_review": "Performance / Raid Review",
        "extreme_builder": "Extreme Builder",
        "comp_maker": "Comp Maker",
        "team_optimization": "Team Optimization",
        "encounter_assignment": "Encounter Assignment",
    }
    return aliases.get(system, system.replace("_", " ").title())


def _policy_details(policy: GameplayPolicy) -> tuple[tuple[str, str], ...]:
    details: list[tuple[str, str]] = [
        ("Authority", "Gameplay-practice policy"),
        ("Role", policy.role.upper() if policy.role != "any" else "Any"),
        ("Content", ", ".join(value.replace("_", " ").title() for value in policy.content_type)),
        ("Default", policy.default_behavior.replace("_", " ").title()),
        ("Confidence", policy.confidence.replace("_", " ").title()),
        ("Subject", policy.subject.replace("_", " ").title()),
    ]
    if policy.exceptions:
        details.append(("Exceptions", "; ".join(value.replace("_", " ") for value in policy.exceptions)))
    if policy.override_contexts:
        details.append(("Override contexts", "; ".join(value.replace("_", " ") for value in policy.override_contexts)))
    if policy.modeling_requirements:
        details.append(("Modeling requirements", "; ".join(value.replace("_", " ") for value in policy.modeling_requirements)))
    return tuple(details)


def _field_note(policy: GameplayPolicy) -> str:
    lines = [policy.summary]
    if policy.rationale:
        lines.append("Why players do this: " + "; ".join(policy.rationale) + ".")
    if policy.explanation_requirement:
        lines.append("Explanation rule: " + policy.explanation_requirement)
    return "\n\n".join(lines)


def entry_from_policy(policy: GameplayPolicy) -> ReferenceEntry:
    presentation = _POLICY_PRESENTATION.get(
        policy.id,
        {
            "name": policy.subject.replace("_", " ").title(),
            "entry_type": "Combat Rule",
            "source_scope": "Player",
            "tags": ("GAMEPLAY POLICY",),
            "related": (),
            "death_note": "No specific death-analysis rule is registered for this reference entry.",
        },
    )
    return ReferenceEntry(
        name=presentation["name"],
        entry_type=presentation["entry_type"],
        source_scope=presentation["source_scope"],
        tags=tuple(presentation["tags"]),
        summary=policy.summary,
        details=_policy_details(policy),
        related=tuple(presentation["related"]),
        death_note=presentation["death_note"],
        field_note=_field_note(policy),
        used_by=tuple(_title_system(value) for value in policy.affected_systems),
        evidence=(f"Gameplay policy: {policy.id}",),
    )


def _yes_no_unknown(value: bool | None) -> str:
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "Not modeled"


def _encounter_mechanic_details(
    encounter: EncounterDefinition,
    mechanic: EncounterMechanic,
) -> tuple[tuple[str, str], ...]:
    details: list[tuple[str, str]] = [
        ("Authority", "Canonical encounter data"),
        ("Encounter", encounter.name),
        ("Content ID", encounter.content_id or "Not recorded"),
        ("Review status", mechanic.interpretation_status or "Not recorded"),
        ("Mechanic type", mechanic.mechanic_type or "Not modeled"),
        ("Damage type", mechanic.damage_type or "Not modeled"),
        ("Target count", str(mechanic.target_count) if mechanic.target_count is not None else "Not modeled"),
        ("Requires movement", _yes_no_unknown(mechanic.requires_movement)),
        ("Requires positioning", _yes_no_unknown(mechanic.requires_positioning)),
        ("Requires cleanse", _yes_no_unknown(mechanic.requires_cleanse)),
        ("Persistent hazard", _yes_no_unknown(mechanic.persistent_hazard)),
        ("Failure is fatal", _yes_no_unknown(mechanic.failure_is_fatal)),
        ("Interruptible", _yes_no_unknown(mechanic.interruptible)),
    ]
    if mechanic.requirement_subjects:
        details.append(
            (
                "Requirement subjects",
                "; ".join(f"{kind}: {subject}" for kind, subject in mechanic.requirement_subjects),
            )
        )
    return tuple(details)


def _encounter_death_note(mechanic: EncounterMechanic) -> str:
    checks: list[str] = []
    if mechanic.failure_is_fatal is True:
        checks.append("The canonical record marks failure of this mechanic as fatal.")
    if mechanic.requires_movement is True:
        checks.append("Check whether the player completed the required movement.")
    if mechanic.requires_positioning is True:
        checks.append("Check positioning at the mechanic window.")
    if mechanic.requires_cleanse is True:
        checks.append("Check cleanse availability and timing.")
    if mechanic.interruptible is True:
        checks.append("Check whether the required interrupt occurred.")
    if not checks:
        return (
            "The canonical encounter record does not currently contain enough structured failure "
            "data to diagnose a death from this mechanic alone."
        )
    return " ".join(checks)


def _encounter_evidence(encounter: EncounterDefinition, mechanic: EncounterMechanic) -> tuple[str, ...]:
    evidence = [f"Canonical mechanic: {mechanic.mechanic_id}"]
    if encounter.source.page_title:
        evidence.append(f"Source page: {encounter.source.page_title}")
    if encounter.source.revision_id:
        evidence.append(f"Source revision: {encounter.source.revision_id}")
    if encounter.source.url:
        evidence.append(f"Source URL: {encounter.source.url}")
    return tuple(evidence)


def entry_from_encounter_mechanic(
    encounter: EncounterDefinition,
    mechanic: EncounterMechanic,
) -> ReferenceEntry:
    tags = ["ENCOUNTER", "MECHANIC"]
    if mechanic.mechanic_type:
        tags.append(str(mechanic.mechanic_type).replace("_", " ").upper())
    if mechanic.damage_type:
        tags.append(str(mechanic.damage_type).replace("_", " ").upper())
    if mechanic.failure_is_fatal is True:
        tags.append("FATAL FAILURE")
    if mechanic.interruptible is True:
        tags.append("INTERRUPTIBLE")

    related = [encounter.name]
    related.extend(phase.label for phase in encounter.phases if phase.label)

    description = mechanic.description.strip() or (
        "Canonical mechanic record exists, but no prose description is currently available."
    )
    return ReferenceEntry(
        name=f"{mechanic.name} — {encounter.name}" if mechanic.name else encounter.name,
        entry_type="Mechanic",
        source_scope="Trial",
        tags=tuple(tags),
        summary=description,
        details=_encounter_mechanic_details(encounter, mechanic),
        related=tuple(dict.fromkeys(related)),
        death_note=_encounter_death_note(mechanic),
        field_note=(
            "Canonical encounter record only. Gameplay-practice handling is not inferred from "
            "mechanic prose; add or link a reviewed practice rule when raid handling is known."
        ),
        used_by=("Encounter System",),
        evidence=_encounter_evidence(encounter, mechanic),
    )


def load_encounter_reference_entries(
    data_root: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    repository = EncounterRepository.from_data_root(data_root or get_data_dir())
    entries: list[ReferenceEntry] = []
    for encounter_id in repository.encounter_ids():
        encounter = repository.get(encounter_id)
        entries.extend(
            entry_from_encounter_mechanic(encounter, mechanic)
            for mechanic in encounter.mechanics
        )
    return tuple(entries)


def _number(value: float | int | None, unit: str = "s") -> str:
    if value is None:
        return "Not modeled"
    number = float(value)
    rendered = str(int(number)) if number.is_integer() else f"{number:g}"
    return f"{rendered} {unit}" if unit else rendered


def _effect_entry_type(effect: CombatEffectReference) -> str:
    category = effect.category.strip().casefold()
    if category == "status":
        return "Status Effect"
    return "Combat Effect"


def entry_from_combat_effect(effect: CombatEffectReference) -> ReferenceEntry:
    details: list[tuple[str, str]] = [
        ("Authority", "Canonical combat-effect data"),
        ("Category", effect.category or "Not recorded"),
        ("Duration", _number(effect.duration)),
        ("Tick interval", _number(effect.tick_interval)),
        ("Maximum stacks", _number(effect.stack_max, "")),
        ("Immunity duration", _number(effect.immunity_duration)),
    ]

    trigger_text: list[str] = []
    for trigger in effect.triggers:
        parts = [trigger.trigger_type]
        if trigger.damage_type:
            parts.append(f"{trigger.damage_type} damage")
        if trigger.weapon_requirement:
            parts.append(f"weapon: {trigger.weapon_requirement}")
        if trigger.condition:
            parts.append(f"condition: {trigger.condition}")
        trigger_text.append(" • ".join(part for part in parts if part))
    if trigger_text:
        details.append(("Triggers", "; ".join(trigger_text)))

    related: list[str] = []
    interaction_text: list[str] = []
    for interaction in effect.interactions:
        related.append(interaction.target_name)
        parts = [f"{interaction.interaction_type} {interaction.target_name}"]
        if interaction.target_value is not None:
            amount = _number(interaction.target_value, interaction.target_unit or "")
            parts.append(amount)
        if interaction.duration is not None:
            parts.append(f"for {_number(interaction.duration)}")
        if interaction.target_scope:
            parts.append(f"scope: {interaction.target_scope}")
        if interaction.condition:
            parts.append(f"condition: {interaction.condition}")
        interaction_text.append(" • ".join(parts))
    if interaction_text:
        details.append(("Interactions", "; ".join(interaction_text)))

    evidence = [f"Canonical combat effect row: {effect.effect_id}"]
    evidence.extend(
        dict.fromkeys(
            source
            for source in (
                *(trigger.raw_source for trigger in effect.triggers),
                *(interaction.raw_source for interaction in effect.interactions),
            )
            if source
        )
    )

    tags = [effect.category.upper() if effect.category else "COMBAT EFFECT"]
    tags.extend(
        trigger.damage_type.upper()
        for trigger in effect.triggers
        if trigger.damage_type
    )

    return ReferenceEntry(
        name=effect.name,
        entry_type=_effect_entry_type(effect),
        source_scope="Global Combat",
        tags=tuple(dict.fromkeys(tags)),
        summary=effect.description.strip() or "Canonical combat-effect record has no description.",
        details=tuple(details),
        related=tuple(dict.fromkeys(related)),
        death_note=(
            "This is a combat-effect reference entry. For a death review, check whether the effect "
            "was active, which source applied it, and whether its documented interaction changed "
            "damage, healing, mitigation, or control at the lethal event."
        ),
        field_note=(
            "Canonical effect data only. Provider choice, expected uptime, and organized-raid "
            "practice belong to the gameplay-policy and team-coverage layers."
        ),
        used_by=(
            "Effects & Buff / Debuff System",
            "Rotation Builder",
            "Comp Maker",
            "Team Optimization",
            "Performance / Raid Review",
        ),
        evidence=tuple(dict.fromkeys(evidence)),
    )


def load_combat_effect_reference_entries(
    database_path: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    service = CombatEffectReferenceService(database_path or (get_data_dir() / "eso.db"))
    return tuple(entry_from_combat_effect(effect) for effect in service.all())


def build_reference_entries(
    policies: Iterable[GameplayPolicy] | None = None,
    *,
    encounters: Iterable[EncounterDefinition] = (),
    effects: Iterable[CombatEffectReference] = (),
    include_encounters: bool = False,
    include_effects: bool = False,
) -> tuple[ReferenceEntry, ...]:
    if policies is None:
        policies = GameplayPolicyService().all()

    rows = [entry_from_policy(policy) for policy in policies]
    rows.extend(
        entry_from_encounter_mechanic(encounter, mechanic)
        for encounter in encounters
        for mechanic in encounter.mechanics
    )
    rows.extend(entry_from_combat_effect(effect) for effect in effects)
    if include_encounters:
        rows.extend(load_encounter_reference_entries())
    if include_effects:
        rows.extend(load_combat_effect_reference_entries())

    return tuple(sorted(rows, key=lambda row: row.name.casefold()))


def entry_types(entries: Iterable[ReferenceEntry]) -> tuple[str, ...]:
    return tuple(sorted({entry.entry_type for entry in entries}, key=str.casefold))


def source_scopes(entries: Iterable[ReferenceEntry]) -> tuple[str, ...]:
    return tuple(sorted({entry.source_scope for entry in entries}, key=str.casefold))
