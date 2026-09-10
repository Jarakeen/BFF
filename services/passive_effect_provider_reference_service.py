from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PassiveEffectProviderReference:
    """Reviewed passive -> named-effect relationship for shared reference consumers.

    This is a provider-relationship authority, not a replacement for the passive's
    owning runtime implementation. Conditions and rank-dependent durations remain
    explicit so callers do not accidentally convert conditional passives into
    permanent standing buffs.
    """

    passive_key: str
    passive_name: str
    eso_class: str
    skill_line: str
    effect_name: str
    relationship: str
    condition: str
    target: str
    duration_rank_1: float | None = None
    duration_rank_2: float | None = None
    game_update: str = "U50"
    evidence: tuple[str, ...] = ()


_REVIEWED_PASSIVE_EFFECTS: tuple[PassiveEffectProviderReference, ...] = (
    PassiveEffectProviderReference(
        passive_key="elder_dragon",
        passive_name="Elder Dragon",
        eso_class="Dragonknight",
        skill_line="Draconic Power",
        effect_name="Minor Brutality",
        relationship="Grants",
        condition="Activate a Draconic Power ability.",
        target="Self and nearby group members",
        duration_rank_1=20.0,
        duration_rank_2=20.0,
        evidence=(
            "services.extreme_dragonknight_draconic_power_passive_review",
            "ESO Update 49 live patch notes",
            "ESO-Hub Elder Dragon",
        ),
    ),
    PassiveEffectProviderReference(
        passive_key="illuminate",
        passive_name="Illuminate",
        eso_class="Templar",
        skill_line="Dawn's Wrath",
        effect_name="Minor Sorcery",
        relationship="Grants",
        condition="Cast a Dawn's Wrath ability.",
        target="Self and group",
        duration_rank_1=10.0,
        duration_rank_2=20.0,
        evidence=(
            "services.extreme_templar_dawns_wrath_passive_review",
            "ESO-Hub Illuminate",
            "U50 named-effect semantics; Minor Sorcery is removed in the modeled U51 table",
        ),
    ),
    PassiveEffectProviderReference(
        passive_key="sacred_ground",
        passive_name="Sacred Ground",
        eso_class="Templar",
        skill_line="Restoring Light",
        effect_name="Minor Mending",
        relationship="Grants",
        condition=(
            "Stand in your own Cleansing Ritual, Rune Focus, or Rite of Passage area; "
            "the effect persists briefly after leaving."
        ),
        target="Self",
        duration_rank_1=2.0,
        duration_rank_2=4.0,
        evidence=(
            "services.extreme_templar_restoring_light_passive_review",
            "ESO-Hub Sacred Ground",
        ),
    ),
    PassiveEffectProviderReference(
        passive_key="accelerated_growth",
        passive_name="Accelerated Growth",
        eso_class="Warden",
        skill_line="Green Balance",
        effect_name="Major Mending",
        relationship="Grants",
        condition="Heal yourself or an ally under 40% Health with a Green Balance ability.",
        target="Self",
        duration_rank_1=2.0,
        duration_rank_2=4.0,
        evidence=(
            "services.extreme_warden_green_balance_passive_review",
            "services.extreme_warden_accelerated_growth_combat_state_service",
            "ESO-Hub Accelerated Growth",
        ),
    ),
    PassiveEffectProviderReference(
        passive_key="maturation",
        passive_name="Maturation",
        eso_class="Warden",
        skill_line="Green Balance",
        effect_name="Minor Toughness",
        relationship="Grants",
        condition="Activate a heal on yourself or an ally.",
        target="Healed target",
        duration_rank_1=10.0,
        duration_rank_2=20.0,
        evidence=(
            "services.extreme_warden_green_balance_passive_review",
            "ESO-Hub Maturation / Minor Toughness",
        ),
    ),
    PassiveEffectProviderReference(
        passive_key="shadow_barrier",
        passive_name="Shadow Barrier",
        eso_class="Nightblade",
        skill_line="Shadow",
        effect_name="Major Resolve",
        relationship="Grants",
        condition=(
            "Cast a Shadow ability; base duration is increased by 2 seconds for each "
            "piece of Heavy Armor equipped."
        ),
        target="Self",
        duration_rank_1=6.0,
        duration_rank_2=12.0,
        evidence=(
            "services.extreme_nightblade_shadow_passive_review",
            "ESO-Hub Shadow Barrier",
        ),
    ),
)


class PassiveEffectProviderReferenceService:
    """Read-only shared access to reviewed passive -> named-effect relationships."""

    def all(self) -> tuple[PassiveEffectProviderReference, ...]:
        return _REVIEWED_PASSIVE_EFFECTS

    def for_effect(self, effect_name: str) -> tuple[PassiveEffectProviderReference, ...]:
        wanted = str(effect_name or "").strip().casefold()
        if not wanted:
            return ()
        return tuple(row for row in self.all() if row.effect_name.casefold() == wanted)

    def for_passive(self, passive_name: str) -> tuple[PassiveEffectProviderReference, ...]:
        wanted = str(passive_name or "").strip().casefold()
        if not wanted:
            return ()
        return tuple(row for row in self.all() if row.passive_name.casefold() == wanted)
