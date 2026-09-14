from __future__ import annotations

"""Resolve human raid-roster gear shorthand to canonical FoundryDock set names.

Raid sheets routinely use short names such as RO, Pill, SoB, LE, and Oz. This
service owns that vocabulary in one place so workbook import, JSON/CSV import,
and one-time repair of older imported builds all make the same decision.

Aliases are exact after punctuation/whitespace normalization. We deliberately do
not use prefix/fuzzy matching: ``Pill`` means Pillager's Profit while ``Pillar``
means Pillar of Nirn, and silently confusing those would be spectacularly unhelpful.

When a roster alias resolves to a set that has a canonical ``Perfected ...`` row,
the Perfected row is preferred. A source can explicitly opt out with ``normal``,
``regular``, ``non-perfected``, or ``non perfected`` before the set name.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
import unicodedata

from minmax.gear_set_repository import GearSetRepository


# Keep this deliberately human-facing. Values are canonical-name hints; the
# resolver validates them against the shipped gear_set table before returning.
_ALIAS_TARGETS: dict[str, str] = {
    # Healer / support
    "ro": "Roaring Opportunist",
    "roaring": "Roaring Opportunist",
    "jorv": "Jorvuld's Guidance",
    "jorvulds": "Jorvuld's Guidance",
    "spc": "Spell Power Cure",
    "pill": "Pillager's Profit",
    "pills": "Pillager's Profit",
    "pillager": "Pillager's Profit",
    "pillagers": "Pillager's Profit",
    "pp": "Pillager's Profit",
    "olo": "Vestment of Olorime",
    "sob": "Symphony of Blades",
    "symphony": "Symphony of Blades",
    "symphonyblades": "Symphony of Blades",
    "oz": "Ozezan the Inferno",
    "ozezan": "Ozezan the Inferno",
    "ozezans": "Ozezan the Inferno",
    "le": "Lucent Echoes",
    "lucent": "Lucent Echoes",
    "echoes": "Lucent Echoes",
    "pearls": "Pearls of Ehlnofey",
    "spauld": "Spaulder of Ruin",
    "spaulder": "Spaulder of Ruin",

    # Tank / support
    "pa": "Powerful Assault",
    "sax": "Saxhleel Champion",
    "saxhleel": "Saxhleel Champion",
    "naz": "Nazaray",
    "nazaray": "Nazaray",
    "archdruid": "Archdruid Devyric",
    "tt": "Turning Tide",
    "turningtide": "Turning Tide",
    "co": "Crimson Oath's Rive",
    "crimson": "Crimson Oath's Rive",
    "yoln": "Claw of Yolnahkriin",
    "tremor": "Tremorscale",
    "tremorscale": "Tremorscale",
    "encratis": "Encratis's Behemoth",

    # Support DD / debuff
    "mk": "Martial Knowledge",
    "zen": "Z'en's Redress",
    "zens": "Z'en's Redress",
    "ec": "Elemental Catalyst",
    "catalyst": "Elemental Catalyst",
    "alkosh": "Roar of Alkosh",
    "morag": "The Morag Tong",
    "mgt": "The Morag Tong",
    "wm": "War Machine",
    # Deliberately no bare "MA": it is too easy to confuse with Maelstrom shorthand.

    # DD staples
    "rele": "Arms of Relequen",
    "relequen": "Arms of Relequen",
    "coral": "Coral Riptide",
    "ansuul": "Ansuul's Torment",
    "sulxan": "Sul-Xan's Torment",
    "whorl": "Whorl of the Depths",
    "pillar": "Pillar of Nirn",
    "kinras": "Kinras's Wrath",
    "ay": "Advancing Yokeda",
    "tzog": "Tzogvin's Warband",
    "mora": "Mora Scribe's Thesis",
    "moras": "Mora Scribe's Thesis",
    "rc": "Runecarver's Blaze",
    "runecarver": "Runecarver's Blaze",
    "cb": "Corpsebuster",
    "corpsebuster": "Corpsebuster",
    "pyrebrand": "Pyrebrand",
    "ow": "Order's Wrath",
    "orders": "Order's Wrath",
    "medusa": "Medusa",
    "levi": "Leviathan",
    "leviathan": "Leviathan",
    "bsw": "Burning Spellweave",
    "briar": "Briarheart",
    "briarheart": "Briarheart",
}


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.replace("’", "'").replace("‘", "'")
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


_ALIAS_BY_KEY = {_normalize(key): value for key, value in _ALIAS_TARGETS.items()}


@dataclass(frozen=True)
class GearSetAliasResolution:
    raw: str
    canonical_name: str
    matched_alias: bool
    perfected: bool
    explicit_non_perfected: bool = False

    @property
    def changed(self) -> bool:
        return bool(self.canonical_name and self.canonical_name != self.raw)


@lru_cache(maxsize=8)
def _canonical_name_index(database_path: str) -> tuple[dict[str, str], frozenset[str]]:
    repository = GearSetRepository(database_path)
    names = tuple(gear_set.name for gear_set in repository.list_sets())
    by_key: dict[str, str] = {}
    for name in names:
        by_key.setdefault(_normalize(name), name)
    return by_key, frozenset(names)


def _strip_explicit_non_perfected(raw: str) -> tuple[str, bool]:
    match = re.match(
        r"^\s*(?:normal|regular|non[\s-]*perfected)\s+(.+?)\s*$",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1).strip(), True
    return raw, False


def resolve_roster_gear_set_name(
    value: object,
    *,
    database_path: str | Path,
    aliases_only: bool = False,
) -> GearSetAliasResolution:
    """Resolve one roster-facing set name.

    ``aliases_only`` is used by the historical repair pass. It changes only
    recognized shorthand, so an intentionally saved full non-Perfected name is
    never upgraded merely because a Perfected sibling exists.
    """

    raw = " ".join(str(value or "").split()).strip()
    if not raw:
        return GearSetAliasResolution(raw="", canonical_name="", matched_alias=False, perfected=False)

    candidate_raw, explicit_non_perfected = _strip_explicit_non_perfected(raw)
    key = _normalize(candidate_raw)
    alias_target = _ALIAS_BY_KEY.get(key)
    matched_alias = alias_target is not None

    if aliases_only and not matched_alias:
        return GearSetAliasResolution(
            raw=raw,
            canonical_name=raw,
            matched_alias=False,
            perfected=raw.casefold().startswith("perfected "),
            explicit_non_perfected=explicit_non_perfected,
        )

    by_key, canonical_names = _canonical_name_index(str(database_path))

    if alias_target is not None:
        base_name = by_key.get(_normalize(alias_target), alias_target)
    else:
        base_name = by_key.get(key, raw)

    # Fail closed if the shipped set table cannot verify the target.
    if _normalize(base_name) not in by_key:
        return GearSetAliasResolution(
            raw=raw,
            canonical_name=raw,
            matched_alias=matched_alias,
            perfected=False,
            explicit_non_perfected=explicit_non_perfected,
        )

    base_name = by_key[_normalize(base_name)]
    if base_name.casefold().startswith("perfected "):
        return GearSetAliasResolution(
            raw=raw,
            canonical_name=base_name,
            matched_alias=matched_alias,
            perfected=True,
            explicit_non_perfected=explicit_non_perfected,
        )

    if not explicit_non_perfected:
        perfected_name = by_key.get(_normalize(f"Perfected {base_name}"))
        if perfected_name and perfected_name in canonical_names:
            return GearSetAliasResolution(
                raw=raw,
                canonical_name=perfected_name,
                matched_alias=matched_alias,
                perfected=True,
                explicit_non_perfected=False,
            )

    return GearSetAliasResolution(
        raw=raw,
        canonical_name=base_name,
        matched_alias=matched_alias,
        perfected=False,
        explicit_non_perfected=explicit_non_perfected,
    )


def roster_gear_set_aliases() -> dict[str, str]:
    """Return a copy for previews, documentation, and tests."""
    return dict(_ALIAS_TARGETS)


__all__ = [
    "GearSetAliasResolution",
    "resolve_roster_gear_set_name",
    "roster_gear_set_aliases",
]
