from __future__ import annotations

"""Reviewed shared-resolver ownership for non-class max-resource passives.

This is a proof ledger, not a second mechanics implementation. Rows are admitted
only when an existing canonical shared resolver or reviewed canonical tooltip
makes the passive's effect family explicit enough to prove whether it can alter
Max Health, Max Magicka, or Max Stamina.
"""

from dataclasses import dataclass
from enum import Enum

from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)

_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


class ExtremeResourceSharedPassiveOwnershipStatus(str, Enum):
    PROVEN_IRRELEVANT = "proven_irrelevant"


@dataclass(frozen=True)
class ExtremeResourceSharedPassiveOwnership:
    domain: ExtremeSkillDomain
    skill_line: str
    passive_name: str
    status: ExtremeResourceSharedPassiveOwnershipStatus
    source: str
    effect_family: str


_REVIEWED_GUILD_IRRELEVANT: tuple[tuple[str, str, str], ...] = (
    ("Dark Brotherhood", "Blade of Woe", "NPC execution interaction only"),
    ("Dark Brotherhood", "Padomaic Sprint", "Major Expedition / movement speed after Blade of Woe kill only"),
    ("Dark Brotherhood", "Scales of Pitiless Justice", "criminal bounty and heat reduction only"),
    ("Dark Brotherhood", "Shadow Rider", "mounted hostile-monster aggression radius only"),
    ("Dark Brotherhood", "Shadowy Supplier", "daily supplier interaction and item grant only"),
    ("Dark Brotherhood", "Spectral Assassin", "Blade of Woe witness/bounty concealment chance only"),
    ("Fighters Guild", "Banish the Wicked", "Ultimate generation on kill only"),
    ("Fighters Guild", "Bounty Hunter", "Cyrodiil bounty-quest access only"),
    ("Fighters Guild", "Intimidating Presence", "NPC intimidation plus Fighters Guild ability Stamina-cost reduction only"),
    ("Fighters Guild", "Skilled Tracker", "Fighters Guild ability damage only"),
    ("Mages Guild", "Everlasting Magic", "Mages Guild ability duration only"),
    ("Mages Guild", "Mage Adept", "Mages Guild ability Magicka/Health cost reduction only"),
    ("Mages Guild", "Might of the Guild", "Empower / Heavy Attack damage only"),
    ("Mages Guild", "Persuasive Will", "NPC persuasion interaction only"),
    ("Psijic Order", "Clairvoyance", "Psijic Order ability cost reduction only"),
    ("Psijic Order", "Concentrated Barrier", "Bracing damage shield only"),
    ("Psijic Order", "Deliberation", "damage-taken mitigation while casting/channeling only"),
    ("Psijic Order", "See the Unseen", "Psijic rift interaction permission only"),
    ("Psijic Order", "Spell Orb", "conditional Magic Damage proc only"),
    ("Thieves Guild", "Clemency", "guard/criminal interaction permission only"),
    ("Thieves Guild", "Finders Keepers", "Thieves Trove interaction permission only"),
    ("Thieves Guild", "Haggling", "fence sale-value modifier only"),
    ("Thieves Guild", "Swiftly Forgotten", "bounty and heat decay only"),
    ("Thieves Guild", "Timely Escape", "Footpad/refuge escape interaction only"),
    ("Thieves Guild", "Veil of Shadows", "witness/guard detection range only"),
)

_REVIEWED_WORLD_IRRELEVANT: tuple[tuple[str, str, str], ...] = (
    ("Soul Magic", "Soul Lock", "Soul Gem/event trigger only; no maximum-resource modification"),
    ("Soul Magic", "Soul Shatter", "death-triggered damage only"),
    ("Soul Magic", "Soul Summons", "resurrection/Soul Gem utility only"),
    ("Vampire", "Blood Ritual", "Vampire infection interaction only"),
    ("Vampire", "Dark Stalker", "Sneak movement and entry timing only"),
    ("Vampire", "Feed", "feeding and Vampire-stage interaction only"),
    ("Vampire", "Strike from the Shadows", "Weapon/Spell Damage after stealth, invisibility, or Mist Form only"),
    ("Vampire", "Undeath", "damage-taken mitigation scaling with missing Health only"),
    ("Vampire", "Unnatural Movement", "sprint cost and invisibility movement state only"),
    ("Werewolf", "Blood Rage", "Werewolf-form duration extension on damage only"),
    ("Werewolf", "Call of the Hunt", "Werewolf-form, Ultimate, and form-maintenance runtime mechanics only"),
    ("Werewolf", "Insatiable Hunger", "healing/current-resource sustain runtime effect; may scale from Max Health but does not modify maxima"),
    ("Werewolf", "Master of the Chase", "movement/chase utility only"),
    ("Werewolf", "Shadow of the Bloodmoon", "Werewolf infection interaction only"),
)


def _reviewed_guild_rows() -> tuple[ExtremeResourceSharedPassiveOwnership, ...]:
    return tuple(
        ExtremeResourceSharedPassiveOwnership(
            domain=ExtremeSkillDomain.GUILD,
            skill_line=skill_line,
            passive_name=passive_name,
            status=ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT,
            source=f"Canonical {skill_line} passive tooltip review",
            effect_family=effect_family,
        )
        for skill_line, passive_name, effect_family in _REVIEWED_GUILD_IRRELEVANT
    )


def _reviewed_world_rows() -> tuple[ExtremeResourceSharedPassiveOwnership, ...]:
    return tuple(
        ExtremeResourceSharedPassiveOwnership(
            domain=ExtremeSkillDomain.WORLD,
            skill_line=skill_line,
            passive_name=passive_name,
            status=ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT,
            source=f"Canonical {skill_line} passive tooltip review",
            effect_family=effect_family,
        )
        for skill_line, passive_name, effect_family in _REVIEWED_WORLD_IRRELEVANT
    )


class ExtremeResourceSharedPassiveOwnershipService:
    """Resolve exact reviewed guild/alliance/weapon/world passive ownership."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    _ROWS = (
        ExtremeResourceSharedPassiveOwnership(
            domain=ExtremeSkillDomain.ALLIANCE_WAR,
            skill_line="Assault",
            passive_name="Combat Frenzy",
            status=ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT,
            source="Canonical Assault passive tooltip review",
            effect_family="Ultimate generation only",
        ),
        ExtremeResourceSharedPassiveOwnership(
            domain=ExtremeSkillDomain.ALLIANCE_WAR,
            skill_line="Assault",
            passive_name="Continuous Attack",
            status=ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT,
            source="Canonical Assault passive tooltip review",
            effect_family="weapon/spell damage, Health/Magicka/Stamina Recovery, and mount speed only",
        ),
        ExtremeResourceSharedPassiveOwnership(
            domain=ExtremeSkillDomain.ALLIANCE_WAR,
            skill_line="Assault",
            passive_name="Reach",
            status=ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT,
            source="Canonical Assault passive tooltip review",
            effect_family="ability range only",
        ),
        ExtremeResourceSharedPassiveOwnership(
            domain=ExtremeSkillDomain.GUILD,
            skill_line="Fighters Guild",
            passive_name="Slayer",
            status=ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT,
            source="GuildPassiveInputResolver",
            effect_family="weapon/spell damage only",
        ),
        ExtremeResourceSharedPassiveOwnership(
            domain=ExtremeSkillDomain.GUILD,
            skill_line="Undaunted",
            passive_name="Undaunted Command",
            status=ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT,
            source="skill_component_resource_restore_display",
            effect_family="current Health/Magicka/Stamina restoration after synergy, scaled from maxima but does not modify maxima",
        ),
        ExtremeResourceSharedPassiveOwnership(
            domain=ExtremeSkillDomain.ALLIANCE_WAR,
            skill_line="Support",
            passive_name="Magicka Aid",
            status=ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT,
            source="AllianceSupportPassiveInputResolver",
            effect_family="magicka recovery only",
        ),
        ExtremeResourceSharedPassiveOwnership(
            domain=ExtremeSkillDomain.WEAPON,
            skill_line="One Hand and Shield",
            passive_name="Fortress",
            status=ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT,
            source="OneHandShieldPassiveInputResolver",
            effect_family="block cost only",
        ),
        ExtremeResourceSharedPassiveOwnership(
            domain=ExtremeSkillDomain.WEAPON,
            skill_line="One Hand and Shield",
            passive_name="Deflect Bolts",
            status=ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT,
            source="OneHandShieldPassiveInputResolver",
            effect_family="block mitigation only",
        ),
    ) + _reviewed_guild_rows() + _reviewed_world_rows()

    @staticmethod
    def _normalized(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @classmethod
    def resolve(
        cls,
        passive: ExtremePlayerSkillRecord,
        objective_key: str,
    ) -> ExtremeResourceSharedPassiveOwnership | None:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme shared-passive objective: {objective_key!r}")

        target = (
            passive.domain,
            cls._normalized(passive.skill_line),
            cls._normalized(passive.name),
        )
        for row in cls._ROWS:
            identity = (
                row.domain,
                cls._normalized(row.skill_line),
                cls._normalized(row.passive_name),
            )
            if identity == target:
                return row
        return None

    @classmethod
    def reviewed(cls) -> tuple[ExtremeResourceSharedPassiveOwnership, ...]:
        return tuple(
            sorted(
                cls._ROWS,
                key=lambda row: (
                    row.domain.value,
                    row.skill_line.casefold(),
                    row.passive_name.casefold(),
                ),
            )
        )
