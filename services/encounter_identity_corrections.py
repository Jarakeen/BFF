from __future__ import annotations

"""Explicit encounter-identity corrections for known source-page misclassification.

UESP content pages can link a creature/species article from a boss list instead of
the named encounter boss. Those generic pages are useful source records, but they
must not become selectable canonical encounters merely because the content page
linked them in a boss-shaped section.

Keep this list narrow and evidence-backed. It is deliberately not a fuzzy
classifier: ambiguous records stay visible until somebody reviews them.
"""


# Blackheart Haven's source crawl historically promoted three generic creature
# pages as bosses. The actual named bosses represented by those creature types
# are separate encounter identities (for example Atarus is an Ogrim). These
# generic pages are not Blackheart Haven boss identities.
_EXCLUDED_ENCOUNTER_IDS_BY_CONTENT: dict[str, frozenset[str]] = {
    "blackheart_haven": frozenset({"ogrim", "hagraven", "skeleton"}),
}

_EXCLUDED_BOSS_TITLES_BY_CONTENT: dict[str, frozenset[str]] = {
    "blackheart_haven": frozenset({"ogrim", "hagraven", "skeleton"}),
}


def encounter_identity_is_excluded(content_id: str, encounter_id: str) -> bool:
    content_key = str(content_id or "").strip().casefold()
    encounter_key = str(encounter_id or "").strip().casefold()
    return encounter_key in _EXCLUDED_ENCOUNTER_IDS_BY_CONTENT.get(content_key, frozenset())


def boss_title_is_excluded(content_id: str, title: str) -> bool:
    content_key = str(content_id or "").strip().casefold()
    title_key = str(title or "").strip().casefold()
    return title_key in _EXCLUDED_BOSS_TITLES_BY_CONTENT.get(content_key, frozenset())
