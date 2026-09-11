from __future__ import annotations

"""Canonical rules that change which equipped item-set bonuses are active.

These rules operate on already-proven equipped set counts. They do not change
physical equipment, traits, glyphs, Mundus, food, race, passives, or any other
non-set contribution.
"""

from collections import Counter
from collections.abc import Mapping


TORC_OF_THE_LAST_AYLEID_KING = "Torc of the Last Ayleid King"


def active_item_set_bonus_counts(equipped_sets: Mapping[str, int]) -> Counter[str]:
    """Return the equipped set counts whose *item-set bonuses* may be active.

    Torc of the Last Ayleid King explicitly disables all other item set bonuses.
    The equipped pieces still exist and remain visible in the source count map;
    only bonus activation is suppressed here.
    """

    counts = Counter(
        {
            str(name): int(count)
            for name, count in equipped_sets.items()
            if str(name or "").strip() and int(count) > 0
        }
    )
    torc_count = int(counts.get(TORC_OF_THE_LAST_AYLEID_KING, 0))
    if torc_count <= 0:
        return counts
    return Counter({TORC_OF_THE_LAST_AYLEID_KING: torc_count})


__all__ = [
    "TORC_OF_THE_LAST_AYLEID_KING",
    "active_item_set_bonus_counts",
]
