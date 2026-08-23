from __future__ import annotations

import re

from ..combat_effect_relationship_repository import CombatEffectInteractionRecord
from .effect_relationship import EffectRelationship, EffectRelationshipType

# Generic ESO-Wiki-wording -> EffectRelationshipType vocabulary. This maps
# words the importer's raw_source data actually uses (see
# importers/combat_effect_importer.py and importers/ability_combat_effect.py)
# onto our relationship types. It is not specific to any named effect -
# any interaction row using one of these words is mapped the same way.
_INTERACTION_TYPE_MAP: dict[str, EffectRelationshipType] = {
    "Applies": EffectRelationshipType.TRIGGERS,
    "Grants": EffectRelationshipType.PROVIDES,
    "Empowers": EffectRelationshipType.MODIFIES,
    "Interacts": EffectRelationshipType.MODIFIES,
}

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def to_effect_identity(display_name: str) -> str:
    """
    Convert an ESO-Hub/ESO-Wiki display name (e.g. "Major Brittle") into
    this project's stable snake_case effect identity (e.g.
    "major_brittle") - the same identity shape EffectVariant.name and
    EffectRelationship use everywhere else. Purely mechanical: it knows
    nothing about any specific effect name.
    """
    slug = _NON_ALNUM.sub("_", display_name.strip().lower()).strip("_")
    return slug


def interaction_record_to_relationship(
    record: CombatEffectInteractionRecord,
) -> EffectRelationship:
    """
    Convert one real CombatEffectInteractionRecord (source effect name ->
    target effect name, from the `combat_effect_interaction` table) into
    a generic EffectRelationship, preserving condition and magnitude.

    This performs no lookup, invention, or classification beyond the
    literal row content - it is a pure, generic shape conversion, reused
    for every interaction row regardless of which named effects it
    involves.
    """
    relationship_type = _INTERACTION_TYPE_MAP.get(
        record.interaction_type, EffectRelationshipType.TRIGGERS
    )

    return EffectRelationship(
        relationship_type=relationship_type,
        source_effect=to_effect_identity(record.source_effect_name),
        target_effect=to_effect_identity(record.target_name),
        magnitude_delta=record.target_value,
        duration=record.duration,
        condition=record.condition,
    )
