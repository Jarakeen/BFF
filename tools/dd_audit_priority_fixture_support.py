from __future__ import annotations

"""Deterministic priority fixtures for DD regression audits.

Production ability priorities are caller-owned gameplay intent.  Regression audits,
however, sometimes need a complete priority list merely so they can compare two
execution paths.  When no explicit priorities are supplied, this helper assigns
strictly increasing priorities in saved front-slot then back-slot order.

The generated ordering is an audit fixture only.  It must never be treated as
canonical gameplay evidence or reused by production Generate composition.
"""

from minmax.rotation_ability_priority import AbilityPriorityEntry
from tools.audit_phase13_dd_priority_schedule import _ordinary_skill_slots, _priority_entries


def deterministic_audit_priorities(build) -> tuple[AbilityPriorityEntry, ...]:
    """Return a complete deterministic audit-only priority fixture for one saved build."""

    entries: list[AbilityPriorityEntry] = []
    priority = 1
    for bar, values in (
        ("front", getattr(build, "FrontBarSkills", [])),
        ("back", getattr(build, "BackBarSkills", [])),
    ):
        for slot, skill_name in _ordinary_skill_slots(values):
            entries.append(
                AbilityPriorityEntry(
                    bar=bar,
                    slot=slot,
                    skill_name=skill_name,
                    priority=priority,
                )
            )
            priority += 1
    return tuple(entries)


def resolve_audit_priorities(
    raw_values: tuple[str, ...],
    *,
    build,
) -> tuple[tuple[AbilityPriorityEntry, ...], bool]:
    """Resolve explicit priorities or an audit-only deterministic fallback.

    Returns ``(entries, used_fixture)``.  Explicit input retains the strict shared
    audit parser, including its requirement that every occupied ordinary slot be
    ranked.  Only a completely absent priority input activates the fixture.
    """

    if raw_values:
        return _priority_entries(raw_values, build=build), False
    return deterministic_audit_priorities(build), True


__all__ = ["deterministic_audit_priorities", "resolve_audit_priorities"]
