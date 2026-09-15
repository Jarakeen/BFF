from __future__ import annotations

"""Compatibility import surface for generated roster drafts.

Canonical persistence now lives in :mod:`services.generated_roster_draft_service`.
Legacy ``GeneratedRosterPlan*`` names remain aliases only while old tools/tests finish
migrating; this module owns no storage or RaidPlan state.
"""

from services.generated_roster_draft_service import (
    GENERATED_ROSTER_DRAFT_OWNERSHIP,
    GENERATED_ROSTER_DRAFT_STORAGE,
    LEGACY_GENERATED_ROSTER_PLAN_READ_MIGRATION_ONLY,
    GeneratedRosterDraft,
    GeneratedRosterDraftService,
    GeneratedRosterDraftSlot,
)


LEGACY_GENERATED_ROSTER_PLAN_COMPATIBILITY = True

GeneratedRosterPlanSlot = GeneratedRosterDraftSlot
GeneratedRosterPlan = GeneratedRosterDraft
GeneratedRosterPlanService = GeneratedRosterDraftService


__all__ = [
    "GENERATED_ROSTER_DRAFT_OWNERSHIP",
    "GENERATED_ROSTER_DRAFT_STORAGE",
    "LEGACY_GENERATED_ROSTER_PLAN_COMPATIBILITY",
    "LEGACY_GENERATED_ROSTER_PLAN_READ_MIGRATION_ONLY",
    "GeneratedRosterDraft",
    "GeneratedRosterDraftService",
    "GeneratedRosterDraftSlot",
    "GeneratedRosterPlan",
    "GeneratedRosterPlanService",
    "GeneratedRosterPlanSlot",
]
