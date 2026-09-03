from __future__ import annotations

"""Read-only Phase 10 closeout audit helpers.

This module separates implementation completeness from local-data readiness. A
tracked placeholder or template is not promoted into a real roster member merely
to satisfy the Phase 10 exit criterion.
"""

from dataclasses import dataclass

from services.saved_build_capability_service import SavedBuildCapabilityAudit


_TEMPLATE_PREFIXES = (
    "your ",
    "template",
    "example",
    "sample",
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def saved_build_identity(audit: SavedBuildCapabilityAudit) -> str:
    return _clean(audit.character_id or audit.character_name or audit.build_name)


def is_real_saved_build(audit: SavedBuildCapabilityAudit) -> bool:
    character = _clean(audit.character_name)
    build = _clean(audit.build_name)
    if not character or not build:
        return False
    lowered = (character.casefold(), build.casefold())
    return not any(
        value.startswith(prefix)
        for value in lowered
        for prefix in _TEMPLATE_PREFIXES
    )


@dataclass(frozen=True)
class Phase10RosterInventory:
    real_builds: tuple[SavedBuildCapabilityAudit, ...]
    template_or_blank_builds: tuple[SavedBuildCapabilityAudit, ...]
    unique_member_ids: tuple[str, ...]
    duplicate_member_ids: tuple[str, ...]

    @property
    def real_build_count(self) -> int:
        return len(self.real_builds)

    @property
    def unique_member_count(self) -> int:
        return len(self.unique_member_ids)

    @property
    def has_multi_member_real_roster(self) -> bool:
        return self.unique_member_count >= 2

    @property
    def has_ambiguous_member_builds(self) -> bool:
        return bool(self.duplicate_member_ids)


def audit_phase10_roster_inventory(
    audits: tuple[SavedBuildCapabilityAudit, ...],
) -> Phase10RosterInventory:
    real = tuple(audit for audit in audits if is_real_saved_build(audit))
    excluded = tuple(audit for audit in audits if not is_real_saved_build(audit))

    counts: dict[str, int] = {}
    ordered_ids: list[str] = []
    for audit in real:
        identity = saved_build_identity(audit)
        if not identity:
            continue
        if identity not in counts:
            ordered_ids.append(identity)
            counts[identity] = 0
        counts[identity] += 1

    duplicates = tuple(identity for identity in ordered_ids if counts[identity] > 1)
    return Phase10RosterInventory(
        real_builds=real,
        template_or_blank_builds=excluded,
        unique_member_ids=tuple(ordered_ids),
        duplicate_member_ids=duplicates,
    )
