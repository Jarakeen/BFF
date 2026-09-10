from __future__ import annotations

"""Reviewed secondary evidence for human-readable Combat Reference gaps.

This module does not replace canonical mechanics/runtime authorities. It records
reviewed research facts that can make Reference Data useful when the canonical
schema does not yet carry a field. Consumers must keep provenance and confidence
visible and must not silently promote these facts into combat math.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewedReferenceFact:
    entry_name: str
    label: str
    value: str
    game_update: str
    confidence: str
    source_tier: str
    source: str
    replaces_label: str | None = None


_STATUS_EFFECT_FACTS: tuple[ReviewedReferenceFact, ...] = (
    ReviewedReferenceFact("Burning", "Delivery", "Damage over time for 4 seconds; canonical corpus records 2-second tick spacing.", "U41+", "high", "official + corroboration", "ESO Update 41 patch notes; ESO-Hub Status Effects"),
    ReviewedReferenceFact("Burning", "Damage association", "Flame Damage", "U41+", "high", "corroborated", "ESO-Hub Status Effects"),
    ReviewedReferenceFact("Chilled", "Delivery", "Instant Frost damage plus control/debuff utility.", "U41+", "high", "official + corroboration", "ESO Update 41 patch notes; ESO-Hub Status Effects"),
    ReviewedReferenceFact("Chilled", "Additional behavior", "Applies Minor Maim for 4 seconds; also applies Minor Brittle when an Ice Staff is the active weapon when Chilled is applied.", "U41+", "high", "corroborated", "ESO-Hub Status Effects"),
    ReviewedReferenceFact("Concussion", "Delivery", "Instant Shock damage.", "U41+", "high", "official + corroboration", "ESO Update 41 patch notes; ESO-Hub Status Effects"),
    ReviewedReferenceFact("Concussion", "Additional behavior", "Applies Minor Vulnerability for 4 seconds and deals additional damage when the target was recently Concussed.", "U41+", "high", "official + corroboration", "ESO Update 41 patch notes; ESO-Hub Status Effects"),
    ReviewedReferenceFact("Diseased", "Delivery", "Instant Disease damage with an additional 6-meter area hit, limited by a 4-second internal cadence for that area component.", "U41+", "high", "official + corroboration", "ESO Update 41 patch notes; ESO-Hub Status Effects"),
    ReviewedReferenceFact("Diseased", "Additional behavior", "Applies Minor Defile for 4 seconds to affected enemies.", "U41+", "high", "official + corroboration", "ESO Update 41 patch notes; ESO-Hub Status Effects"),
    ReviewedReferenceFact("Hemorrhaging", "Delivery", "Bleed damage over 4 seconds; canonical corpus records 2-second tick spacing.", "U41+", "high", "official + corroboration", "ESO Update 41 patch notes; ESO-Hub Status Effects"),
    ReviewedReferenceFact("Hemorrhaging", "Stack behavior", "Stacks up to 3 times; Update 41 removed its former Minor Mangle application.", "U41+", "high", "official", "ESO Update 41 patch notes"),
    ReviewedReferenceFact("Overcharged", "Delivery", "Instant Magic damage.", "U41+", "high", "official + corroboration", "ESO Update 41 patch notes; ESO-Hub Status Effects"),
    ReviewedReferenceFact("Overcharged", "Additional behavior", "Instantly restores 65 Magicka to the activator and applies Minor Magickasteal for 4 seconds.", "U41+", "high", "official + corroboration", "ESO Update 41 patch notes; ESO-Hub Status Effects"),
    ReviewedReferenceFact("Poisoned", "Delivery", "Poison damage over 4 seconds; canonical corpus records 2-second tick spacing.", "U41+", "high", "official + corroboration", "ESO Update 41 patch notes; ESO-Hub Status Effects"),
    ReviewedReferenceFact("Poisoned", "Additional behavior", "Execute-style damage that scales up as the target loses Health, up to 100% bonus damage.", "U41+", "high", "official + corroboration", "ESO Update 41 patch notes; ESO-Hub Status Effects"),
    ReviewedReferenceFact("Sundered", "Delivery", "Instant Physical damage.", "U41+", "high", "official + corroboration", "ESO Update 41 patch notes; ESO-Hub Status Effects"),
    ReviewedReferenceFact("Sundered", "Additional behavior", "Applies Minor Breach and grants the activator 100 Weapon and Spell Damage for 4 seconds.", "U41+", "high", "official + corroboration", "ESO Update 41 patch notes; ESO-Hub Status Effects"),
)

_COMBAT_EFFECT_FACTS: tuple[ReviewedReferenceFact, ...] = (
    ReviewedReferenceFact("Off Balance", "Player-source window", "Player-sourced Off Balance lasts 7 seconds.", "U25+", "high", "official", "ESO PTS v5.3.0 / Update 25 combat changes"),
    ReviewedReferenceFact("Off Balance", "Reapplication lockout", "After the original player-sourced Off Balance ends, it cannot be reapplied to that target for 15 seconds; the cooldown is displayed as a debuff.", "U25+", "high", "official", "ESO PTS v5.3.0 / Update 25 combat changes"),
    ReviewedReferenceFact("Off Balance", "Consumption rule", "Heavy Attacks and abilities do not consume Off Balance.", "U25+", "high", "official", "ESO PTS v5.3.0 / Update 25 combat changes"),
    ReviewedReferenceFact("Hindered", "Encounter context", "Dreadsail Reef heavy-attack consequence when the relevant heavy is blocked and not fully absorbed by a shield.", "U34+", "medium-high", "guide + PTS corroboration", "ESO-Hub Dreadsail Reef guide by Qcell; Update 34 PTS feedback"),
    ReviewedReferenceFact("Hindered", "Effect", "Prevents healing missing Health for 12 seconds or until roughly 39.7k healing is received to remove the absorption; guide evidence says it cannot be purged by negative-effect removal skills.", "U34+", "medium-high", "guide + PTS corroboration", "ESO-Hub Dreadsail Reef guide by Qcell; Update 34 PTS feedback"),
    ReviewedReferenceFact("Rattled", "Encounter context", "Dreadsail Reef heavy-attack consequence paired with Hindered on a correctly blocked, not-fully-shielded heavy.", "U34+", "medium-high", "guide + PTS corroboration", "ESO-Hub Dreadsail Reef guide by Qcell; Update 34 PTS feedback"),
    ReviewedReferenceFact("Rattled", "Effect", "For 12 seconds, damage done is reduced by 70% and damage taken is increased by 40%; guide evidence says it cannot be purged by negative-effect removal skills.", "U34+", "medium-high", "guide + PTS corroboration", "ESO-Hub Dreadsail Reef guide by Qcell; Update 34 PTS feedback"),
    ReviewedReferenceFact("Devitalized", "Encounter context", "Dreadsail Reef heavy-attack consequence when the relevant heavy is not blocked or is fully absorbed by a shield.", "U34+", "medium-high", "guide + PTS corroboration", "ESO-Hub Dreadsail Reef guide by Qcell; Update 34 PTS feedback"),
    ReviewedReferenceFact("Devitalized", "Effect", "For 8 seconds, Physical and Spell Resistance are reduced by 60%, damage taken is increased by 30%, and damage shields are reduced by 30%; guide evidence says it cannot be purged by negative-effect removal skills.", "U34+", "medium-high", "guide + PTS corroboration", "ESO-Hub Dreadsail Reef guide by Qcell; Update 34 PTS feedback"),
)

_NAMED_EFFECT_FACTS: tuple[ReviewedReferenceFact, ...] = (
    ReviewedReferenceFact("Minor Berserk", "Standard effect", "Increases damage done by 5%.", "U28+", "high", "official + corroboration", "ESO Update 28 patch notes; ESO-Hub Minor Berserk"),
    ReviewedReferenceFact("Major Berserk", "Standard effect", "Increases damage done by 10%.", "U28+", "high", "official + corroboration", "ESO Update 28 patch notes; ESO-Hub Major Berserk"),
    ReviewedReferenceFact("Minor Protection", "Standard effect", "Reduces damage taken by 5%.", "U28+", "high", "official + corroboration", "ESO Update 28 patch notes; ESO-Hub Minor Protection"),
    ReviewedReferenceFact("Major Protection", "Standard effect", "Reduces damage taken by 10%.", "U28+", "high", "official + corroboration", "ESO Update 28 patch notes; ESO-Hub Major Protection"),
    ReviewedReferenceFact("Minor Vulnerability", "Standard effect", "Increases damage taken by 5%.", "U28+", "high", "official + corroboration", "ESO Update 28 patch notes; ESO-Hub Minor Vulnerability"),
    ReviewedReferenceFact("Major Vulnerability", "Standard effect", "Increases damage taken by 10%.", "U28+", "high", "official + corroboration", "ESO Update 28 patch notes; ESO-Hub Major Vulnerability"),
    ReviewedReferenceFact("Minor Slayer", "Standard effect", "Increases damage done to Dungeon, Trial, and Arena monsters by 5%.", "U28+", "high", "official + corroboration", "ESO Update 28 standardization; ESO-Hub Minor Slayer and trial-set tooltips"),
    ReviewedReferenceFact("Major Slayer", "Standard effect", "Increases damage done to Dungeon, Trial, and Arena monsters by 10%.", "U28+", "high", "official + corroboration", "ESO Update 28 standardization; ESO-Hub Major Slayer and trial-set tooltips"),
    ReviewedReferenceFact("Minor Aegis", "Standard effect", "Reduces damage taken from Dungeon, Trial, and Arena monsters by 5%.", "U28+", "high", "official + corroboration", "ESO Update 28 standardization; ESO-Hub Minor Aegis and trial-set tooltips"),
    ReviewedReferenceFact("Major Aegis", "Standard effect", "Reduces damage taken from Dungeon, Trial, and Arena monsters by 10%.", "U28+", "high", "official + corroboration", "ESO Update 28 standardization; ESO-Hub Major Aegis and trial-set tooltips"),
    ReviewedReferenceFact("Minor Vitality", "Standard effect", "Increases healing received and damage shield strength by 6%.", "U41+", "high", "official + corroboration", "ESO Update 41 patch notes; ESO-Hub Minor Vitality"),
    ReviewedReferenceFact("Major Vitality", "Standard effect", "Increases healing received and damage shield strength by 12%.", "U41+", "high", "official + corroboration", "ESO Update 41 patch notes; ESO-Hub Major Vitality"),
    ReviewedReferenceFact("Minor Defile", "Standard effect", "Reduces healing received and damage shield strength by 6%.", "U41+", "high", "official + corroboration", "ESO Update 41 patch notes; ESO-Hub Minor Defile"),
    ReviewedReferenceFact("Major Defile", "Standard effect", "Reduces healing received and damage shield strength by 12%.", "U41+", "high", "official + corroboration", "ESO Update 41 patch notes; ESO-Hub Major Defile"),
)

_XALVAKKA_FACTS: tuple[ReviewedReferenceFact, ...] = (
    ReviewedReferenceFact("Deadstar — Xalvakka", "Movement requirement", "Yes. Deadstar places large red-circle meteor impacts that should be moved out of rather than intentionally eaten.", "U30+", "medium-high", "canonical corpus + guide corroboration", "BFF Xalvakka canonical source record; Xynode Rockgrove guide", "Requires movement"),
    ReviewedReferenceFact("Deadstar — Xalvakka", "Target pattern", "Three sequential meteors are placed at player locations; treat this as repeated ground targeting rather than one fixed target-count event.", "U30+", "medium-high", "canonical corpus + guide corroboration", "BFF Xalvakka canonical source record; Xynode Rockgrove guide"),
    ReviewedReferenceFact("Summon Wraiths — Xalvakka", "Failure severity", "Potential group wipe. Wraiths that reach Xalvakka add shield strength; enough absorbed wraiths can make the shield unbreakable and wipe the group.", "U30+", "high", "canonical corpus", "BFF Xalvakka canonical source record", "Failure is fatal"),
    ReviewedReferenceFact("Soul Resonance — Xalvakka", "Persistent hazard", "Yes. Using Soul Purge leaves Corrupted Azureplasm at the purge location; the pool heavily slows players and later explodes.", "U30+", "high", "canonical corpus", "BFF Xalvakka canonical source record", "Persistent hazard"),
    ReviewedReferenceFact("Soul Resonance — Xalvakka", "Handling", "Cleanse with the Soul Purge synergy and place the resulting Azureplasm deliberately away from movement paths and group stack locations.", "U30+", "medium-high", "canonical corpus + guide context", "BFF Xalvakka canonical source record; Xynode Rockgrove guide"),
    ReviewedReferenceFact("Split — Xalvakka", "Persistent hazard", "Yes. During the split the arena floor is engulfed in continuous flame damage except for limited safe ground around the copies.", "U30+", "high", "canonical corpus + guide corroboration", "BFF Xalvakka canonical source record; Xynode Rockgrove guide", "Persistent hazard"),
    ReviewedReferenceFact("Split — Xalvakka", "Movement requirement", "Yes. The group must relocate through the limited safe areas while identifying and attacking the real Xalvakka copy.", "U30+", "medium-high", "canonical corpus + guide corroboration", "BFF Xalvakka canonical source record; Xynode Rockgrove guide", "Requires movement"),
    ReviewedReferenceFact("Corrupted Blast — Xalvakka", "Scaling", "Damage increases with the number of wraiths Xalvakka has absorbed while her shield is active.", "U30+", "high", "canonical corpus", "BFF Xalvakka canonical source record"),
)

_ALL_FACTS = (*_STATUS_EFFECT_FACTS, *_COMBAT_EFFECT_FACTS, *_NAMED_EFFECT_FACTS, *_XALVAKKA_FACTS)


class ReferenceResearchEnrichmentService:
    """Read-only reviewed research facts keyed by human-readable reference entry."""

    def facts_for(self, entry_name: str) -> tuple[ReviewedReferenceFact, ...]:
        wanted = str(entry_name or "").strip().casefold()
        if not wanted:
            return ()
        return tuple(fact for fact in _ALL_FACTS if fact.entry_name.casefold() == wanted)

    def all(self) -> tuple[ReviewedReferenceFact, ...]:
        return _ALL_FACTS
