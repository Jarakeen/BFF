from __future__ import annotations

"""Verified named combat buffs and their routing layer.

U50 remains the default until Update 51 is live. U51 changes are expressed as
versioned semantics rather than by mutating historical U50 definitions.
"""

from dataclasses import dataclass

from .combat_effect_semantics import GameUpdate, normalize_game_update, resolve_buff_name
from .stat_ids import StatId


@dataclass(frozen=True)
class NamedBuffEffect:
    stat: StatId
    value: float
    bucket: str


U50_NAMED_BUFF_EFFECTS: dict[str, tuple[NamedBuffEffect, ...]] = {
    "Minor Brutality": (NamedBuffEffect(StatId.WEAPON_DAMAGE, 0.10, "percent"),),
    "Major Brutality": (NamedBuffEffect(StatId.WEAPON_DAMAGE, 0.20, "percent"),),
    "Minor Sorcery": (NamedBuffEffect(StatId.SPELL_DAMAGE, 0.10, "percent"),),
    "Major Sorcery": (NamedBuffEffect(StatId.SPELL_DAMAGE, 0.20, "percent"),),
    "Minor Courage": (
        NamedBuffEffect(StatId.WEAPON_DAMAGE, 215.0, "flat"),
        NamedBuffEffect(StatId.SPELL_DAMAGE, 215.0, "flat"),
    ),
    "Major Courage": (
        NamedBuffEffect(StatId.WEAPON_DAMAGE, 430.0, "flat"),
        NamedBuffEffect(StatId.SPELL_DAMAGE, 430.0, "flat"),
    ),
    "Minor Savagery": (NamedBuffEffect(StatId.WEAPON_CRITICAL, 1314.0, "critical_rating"),),
    "Major Savagery": (NamedBuffEffect(StatId.WEAPON_CRITICAL, 2629.0, "critical_rating"),),
    "Minor Prophecy": (NamedBuffEffect(StatId.SPELL_CRITICAL, 1314.0, "critical_rating"),),
    "Major Prophecy": (NamedBuffEffect(StatId.SPELL_CRITICAL, 2629.0, "critical_rating"),),
    "Minor Force": (NamedBuffEffect(StatId.CRITICAL_DAMAGE, 0.10, "ratio_points"),),
    "Major Force": (NamedBuffEffect(StatId.CRITICAL_DAMAGE, 0.20, "ratio_points"),),
    "Minor Mending": (NamedBuffEffect(StatId.HEALING_DONE, 0.08, "ratio_points"),),
    "Major Mending": (NamedBuffEffect(StatId.HEALING_DONE, 0.16, "ratio_points"),),
    "Minor Resolve": (
        NamedBuffEffect(StatId.PHYSICAL_RESISTANCE, 2974.0, "flat"),
        NamedBuffEffect(StatId.SPELL_RESISTANCE, 2974.0, "flat"),
    ),
    "Major Resolve": (
        NamedBuffEffect(StatId.PHYSICAL_RESISTANCE, 5948.0, "flat"),
        NamedBuffEffect(StatId.SPELL_RESISTANCE, 5948.0, "flat"),
    ),
    "Minor Fortitude": (NamedBuffEffect(StatId.HEALTH_RECOVERY, 0.15, "resource_percent"),),
    "Major Fortitude": (NamedBuffEffect(StatId.HEALTH_RECOVERY, 0.30, "resource_percent"),),
    "Minor Intellect": (NamedBuffEffect(StatId.MAGICKA_RECOVERY, 0.15, "resource_percent"),),
    "Major Intellect": (NamedBuffEffect(StatId.MAGICKA_RECOVERY, 0.30, "resource_percent"),),
    "Minor Endurance": (NamedBuffEffect(StatId.STAMINA_RECOVERY, 0.15, "resource_percent"),),
    "Major Endurance": (NamedBuffEffect(StatId.STAMINA_RECOVERY, 0.30, "resource_percent"),),
    "Minor Toughness": (NamedBuffEffect(StatId.MAX_HEALTH, 0.10, "resource_percent"),),
}

# Compatibility alias retained for existing callers/tests that inspect the map.
NAMED_BUFF_EFFECTS = U50_NAMED_BUFF_EFFECTS

U51_NAMED_BUFF_EFFECTS: dict[str, tuple[NamedBuffEffect, ...]] = dict(U50_NAMED_BUFF_EFFECTS)
U51_NAMED_BUFF_EFFECTS.update(
    {
        "Minor Brutality": (
            NamedBuffEffect(StatId.WEAPON_DAMAGE, 0.10, "percent"),
            NamedBuffEffect(StatId.SPELL_DAMAGE, 0.10, "percent"),
        ),
        "Major Brutality": (
            NamedBuffEffect(StatId.WEAPON_DAMAGE, 0.20, "percent"),
            NamedBuffEffect(StatId.SPELL_DAMAGE, 0.20, "percent"),
        ),
        "Minor Savagery": (
            NamedBuffEffect(StatId.WEAPON_CRITICAL, 1314.0, "critical_rating"),
            NamedBuffEffect(StatId.SPELL_CRITICAL, 1314.0, "critical_rating"),
        ),
        "Major Savagery": (
            NamedBuffEffect(StatId.WEAPON_CRITICAL, 2629.0, "critical_rating"),
            NamedBuffEffect(StatId.SPELL_CRITICAL, 2629.0, "critical_rating"),
        ),
    }
)
# Removed U51 names are intentionally absent. Strict source resolution therefore
# cannot accidentally apply obsolete Sorcery/Prophecy semantics.
for _removed in ("Minor Sorcery", "Major Sorcery", "Minor Prophecy", "Major Prophecy"):
    U51_NAMED_BUFF_EFFECTS.pop(_removed, None)

# Known named effects whose semantics belong to a later component calculation,
# not the shared standing/stat layer. Values are resolved by that owning layer.
COMPONENT_LAYER_BUFFS = frozenset({
    "Minor Berserk",
    "Major Berserk",
    "Minor Protection",
    "Major Protection",
    "Minor Vulnerability",
    "Major Vulnerability",
})


def canonical_buff_name(value: str) -> str | None:
    key = " ".join(str(value or "").strip().casefold().split())
    if not key:
        return None
    names = set(U50_NAMED_BUFF_EFFECTS) | set(U51_NAMED_BUFF_EFFECTS) | set(COMPONENT_LAYER_BUFFS)
    for name in names:
        if name.casefold() == key:
            return name
    return None


def effects_for_buff(
    value: str,
    *,
    game_update: GameUpdate | str = GameUpdate.U50,
    allow_legacy_alias: bool = False,
) -> tuple[NamedBuffEffect, ...]:
    update = normalize_game_update(game_update)
    canonical = canonical_buff_name(value)
    if canonical is None:
        return ()
    resolved = resolve_buff_name(
        canonical,
        game_update=update,
        allow_legacy_alias=allow_legacy_alias,
    )
    if resolved is None:
        return ()
    table = U50_NAMED_BUFF_EFFECTS if update is GameUpdate.U50 else U51_NAMED_BUFF_EFFECTS
    return table.get(resolved, ())


def is_component_layer_buff(value: str) -> bool:
    canonical = canonical_buff_name(value)
    return bool(canonical and canonical in COMPONENT_LAYER_BUFFS)
