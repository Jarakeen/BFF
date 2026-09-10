from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

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


def build_reference_entries(
    policies: Iterable[GameplayPolicy] | None = None,
) -> tuple[ReferenceEntry, ...]:
    if policies is None:
        policies = GameplayPolicyService().all()
    return tuple(sorted((entry_from_policy(policy) for policy in policies), key=lambda row: row.name.casefold()))


def entry_types(entries: Iterable[ReferenceEntry]) -> tuple[str, ...]:
    return tuple(sorted({entry.entry_type for entry in entries}, key=str.casefold))


def source_scopes(entries: Iterable[ReferenceEntry]) -> tuple[str, ...]:
    return tuple(sorted({entry.source_scope for entry in entries}, key=str.casefold))
