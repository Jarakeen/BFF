from __future__ import annotations

"""Hide explicitly reviewed false encounter identities from boss-guide selectors.

This is intentionally narrow. It does not guess whether an arbitrary encounter
looks generic; it applies only tracked corrections from
``services.encounter_identity_corrections`` so source data remains lossless while
known-bad selector identities stop leaking into the UI.
"""

from services.encounter_boss_guide import EncounterBossGuideService
from services.encounter_identity_corrections import encounter_identity_is_excluded


_INSTALLED = False


def _filter_summaries(rows):
    return tuple(
        row
        for row in rows
        if not encounter_identity_is_excluded(row.content_id, row.encounter_id)
    )


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    original_summaries = EncounterBossGuideService.encounter_summaries

    def corrected_summaries(service):
        return _filter_summaries(original_summaries(service))

    EncounterBossGuideService.encounter_summaries = corrected_summaries
    _INSTALLED = True
