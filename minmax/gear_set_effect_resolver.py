from __future__ import annotations

import re

from .effect_kinds import EffectKind
from .effects import Effect, EffectOperation, EffectUnit
from .gear_sets import GearSetBonus
from .stat_ids import StatId


class GearSetEffectResolver:
    """Resolve reviewed static/conditional gear-set bonuses into Effects.

    Triggered, proc, cooldown, scaling, and trade-off bonuses remain unresolved
    unless their full mechanic can be represented without guessing.
    """

    _COLOR_MARKUP = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")
    _BONUS_PREFIX = re.compile(
        r"^\(\d+\s+(?:perfected\s+)?items?\)\s*",
        re.IGNORECASE,
    )
    _RANGE = r"(?P<min>\d[\d,]*)\s*-\s*(?P<max>\d[\d,]*)"
    _NUMBER = r"(?P<value>\d+(?:\.\d+)?)"

    _FLAT_STATS = {
        "Maximum Health": StatId.MAX_HEALTH,
        "Maximum Magicka": StatId.MAX_MAGICKA,
        "Maximum Stamina": StatId.MAX_STAMINA,
        "Health Recovery": StatId.HEALTH_RECOVERY,
        "Magicka Recovery": StatId.MAGICKA_RECOVERY,
        "Stamina Recovery": StatId.STAMINA_RECOVERY,
        "Critical Chance": StatId.CRITICAL_CHANCE,
        "Critical Resistance": StatId.CRITICAL_RESISTANCE,
    }

    def resolve(
        self,
        bonus: GearSetBonus,
        *,
        use_max_value: bool = True,
        source: str | None = None,
    ) -> list[Effect]:
        description = bonus.description
        if not description:
            return []

        text = self._clean_description(description)
        if not text:
            return []

        source_text = source or f"Gear set bonus ({bonus.piece_count} items)"

        combined = self._resolve_combined(text, source_text, use_max_value)
        if combined:
            return combined

        for label, stat in self._FLAT_STATS.items():
            match = re.fullmatch(
                rf"Adds\s+{self._RANGE}\s+{re.escape(label)}",
                text,
                re.IGNORECASE,
            )
            if match:
                value = self._selected_range_value(match, use_max_value)
                return [self._effect(stat, value, source_text)]

        for label, stat in self._FLAT_STATS.items():
            match = re.fullmatch(
                rf"Adds\s+{self._NUMBER}\s+{re.escape(label)}",
                text,
                re.IGNORECASE,
            )
            if match:
                value = float(match.group("value"))
                return [self._effect(stat, value, source_text)]

        percent_patterns = (
            (r"Adds\s+(?P<value>\d+(?:\.\d+)?)%\s+Healing Done", StatId.HEALING_DONE),
            (r"Adds\s+(?P<value>\d+(?:\.\d+)?)%\s+Healing Taken", StatId.HEALING_TAKEN),
            (
                r"Increases your healing received by\s+(?P<value>\d+(?:\.\d+)?)%\.?",
                StatId.HEALING_TAKEN,
            ),
        )
        for pattern, stat in percent_patterns:
            match = re.fullmatch(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group("value"))
                return [self._effect(
                    stat,
                    value,
                    source_text,
                    operation=EffectOperation.ADD_PERCENT,
                    unit=EffectUnit.PERCENT,
                )]

        conditional = self._resolve_conditional_percentage(
            text,
            source_text,
        )
        if conditional:
            return conditional

        conditional = self._resolve_state_conditional_stats(
            text,
            source_text,
            use_max_value,
        )
        if conditional:
            return conditional

        stealth = self._resolve_stealth_stats(
            text,
            source_text,
            use_max_value,
        )
        if stealth:
            return stealth

        conditional = self._resolve_ability_scoped_damage(
            text,
            source_text,
            use_max_value,
        )
        if conditional:
            return conditional

        percent_stats = {
            "Healing Done": StatId.HEALING_DONE,
            "Healing Taken": StatId.HEALING_TAKEN,
            "Critical Resistance": StatId.CRITICAL_RESISTANCE,
        }
        for label, stat in percent_stats.items():
            match = re.fullmatch(
                rf"Increases your\s+{re.escape(label)}\s+by\s+(?P<value>\d+(?:\.\d+)?)%",
                text,
                re.IGNORECASE,
            )
            if match:
                return [self._effect(
                    stat,
                    float(match.group("value")),
                    source_text,
                    operation=EffectOperation.ADD_PERCENT,
                    unit=EffectUnit.PERCENT,
                )]

        return []

    def _resolve_conditional_percentage(
        self,
        text: str,
        source: str,
    ) -> list[Effect]:
        match = re.fullmatch(
            r"Increases your Critical Damage and Healing by "
            r"(?P<base>\d+(?:\.\d+)?)%\.\s*"
            r"Increases your Critical Damage and Healing by an additional "
            r"(?P<conditional>\d+(?:\.\d+)?)%\s+"
            r"when you are Sneaking or Invisible\.",
            text,
            re.IGNORECASE,
        )

        if not match:
            return []

        base = float(match.group("base"))
        conditional = float(match.group("conditional"))

        return [
            self._effect(
                StatId.CRITICAL_DAMAGE,
                base,
                source,
                operation=EffectOperation.ADD_PERCENT,
                unit=EffectUnit.PERCENT,
            ),
            self._effect(
                StatId.HEALING_DONE,
                base,
                source,
                operation=EffectOperation.ADD_PERCENT,
                unit=EffectUnit.PERCENT,
            ),
            self._effect(
                StatId.CRITICAL_DAMAGE,
                conditional,
                source,
                operation=EffectOperation.ADD_PERCENT,
                unit=EffectUnit.PERCENT,
                condition="sneaking_or_invisible",
            ),
            self._effect(
                StatId.HEALING_DONE,
                conditional,
                source,
                operation=EffectOperation.ADD_PERCENT,
                unit=EffectUnit.PERCENT,
                condition="sneaking_or_invisible",
            ),
        ]

    def _resolve_state_conditional_stats(
        self,
        text: str,
        source: str,
        use_max_value: bool,
    ) -> list[Effect]:
        single_patterns = (
            (
                r"While you have a damage shield on you, your Health Recovery is increased by "
                rf"{self._RANGE}\. ?",
                (StatId.HEALTH_RECOVERY,),
                "damage_shield_active",
            ),
            (
                r"While you have a Destruction Staff equipped, your Max Magicka is increased by "
                rf"{self._RANGE}\. ?",
                (StatId.MAX_MAGICKA,),
                "destruction_staff_equipped",
            ),
        )
        for pattern, stats, condition in single_patterns:
            match = re.fullmatch(pattern, text, re.IGNORECASE)
            if match:
                value = self._selected_range_value(match, use_max_value)
                return [
                    self._effect(stat, value, source, condition=condition)
                    for stat in stats
                ]

        match = re.fullmatch(
            r"While you are standing still, you gain "
            r"(?P<wd_min>\d[\d,]*)\s*-\s*(?P<wd_max>\d[\d,]*) Weapon and Spell Damage\.\s*"
            r"While you are moving, you gain "
            r"(?P<rec_min>\d[\d,]*)\s*-\s*(?P<rec_max>\d[\d,]*) "
            r"Health, Magicka, and Stamina Recovery\. ?",
            text,
            re.IGNORECASE,
        )
        if match:
            damage_key = "wd_max" if use_max_value else "wd_min"
            recovery_key = "rec_max" if use_max_value else "rec_min"
            damage = float(match.group(damage_key).replace(",", ""))
            recovery = float(match.group(recovery_key).replace(",", ""))
            return [
                self._effect(StatId.WEAPON_DAMAGE, damage, source, condition="standing_still"),
                self._effect(StatId.SPELL_DAMAGE, damage, source, condition="standing_still"),
                self._effect(StatId.HEALTH_RECOVERY, recovery, source, condition="moving"),
                self._effect(StatId.MAGICKA_RECOVERY, recovery, source, condition="moving"),
                self._effect(StatId.STAMINA_RECOVERY, recovery, source, condition="moving"),
            ]

        match = re.fullmatch(
            r"While Bracing, increase your Magicka Recovery by (?P<mag>\d+(?:\.\d+)?)\.\s*"
            r"While you are not Bracing, increase your Stamina Recovery by (?P<stam>\d+(?:\.\d+)?)\. ?",
            text,
            re.IGNORECASE,
        )
        if match:
            return [
                self._effect(
                    StatId.MAGICKA_RECOVERY,
                    float(match.group("mag")),
                    source,
                    condition="bracing",
                ),
                self._effect(
                    StatId.STAMINA_RECOVERY,
                    float(match.group("stam")),
                    source,
                    condition="not_bracing",
                ),
            ]

        return []

    def _resolve_stealth_stats(
        self,
        text: str,
        source: str,
        use_max_value: bool,
    ) -> list[Effect]:
        match = re.fullmatch(
            r"Reduces the radius you can be detected while Sneaking by "
            r"(?P<radius>\d+(?:\.\d+)?) meters?\.\s*"
            r"Reduces the cost of Sneak by "
            r"(?P<cost_min>\d+(?:\.\d+)?)\s*-\s*(?P<cost_max>\d+(?:\.\d+)?)%\. ?",
            text,
            re.IGNORECASE,
        )
        if not match:
            return []

        cost_key = "cost_max" if use_max_value else "cost_min"
        return [
            self._effect(
                StatId.DETECTION_RADIUS_REDUCTION,
                float(match.group("radius")),
                source,
            ),
            self._effect(
                StatId.SNEAK_COST_REDUCTION,
                float(match.group(cost_key)),
                source,
                operation=EffectOperation.ADD_PERCENT,
                unit=EffectUnit.PERCENT,
            ),
        ]

    def _resolve_ability_scoped_damage(
        self,
        text: str,
        source: str,
        use_max_value: bool,
    ) -> list[Effect]:
        match = re.fullmatch(
            rf"Adds\s+{self._RANGE}\s+Weapon and Spell Damage to your "
            r"(?P<scope>.+?) abilities\.?",
            text,
            re.IGNORECASE,
        )
        if not match:
            return []

        value = self._selected_range_value(match, use_max_value)
        scope = self._condition_slug(match.group("scope"))
        condition = f"ability_scope:{scope}"
        return [
            self._effect(StatId.WEAPON_DAMAGE, value, source, condition=condition),
            self._effect(StatId.SPELL_DAMAGE, value, source, condition=condition),
        ]

    def _resolve_combined(
        self,
        text: str,
        source: str,
        use_max_value: bool,
    ) -> list[Effect]:
        combined = (
            (
                "Weapon and Spell Damage",
                (StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE),
            ),
            (
                "Armor",
                (StatId.PHYSICAL_RESISTANCE, StatId.SPELL_RESISTANCE),
            ),
            (
                "Offensive Penetration",
                (StatId.PHYSICAL_PENETRATION, StatId.SPELL_PENETRATION),
            ),
        )

        for label, stats in combined:
            match = re.fullmatch(
                rf"Adds\s+{self._RANGE}\s+{re.escape(label)}",
                text,
                re.IGNORECASE,
            )
            if match:
                value = self._selected_range_value(match, use_max_value)
                return [
                    self._effect(stat, value, source)
                    for stat in stats
                ]

            match = re.fullmatch(
                rf"Adds\s+{self._NUMBER}\s+{re.escape(label)}",
                text,
                re.IGNORECASE,
            )
            if match:
                value = float(match.group("value"))
                return [
                    self._effect(stat, value, source)
                    for stat in stats
                ]

        return []

    @classmethod
    def _clean_description(cls, description: str) -> str:
        text = cls._COLOR_MARKUP.sub("", description).strip()
        text = cls._BONUS_PREFIX.sub("", text).strip()
        return text

    @staticmethod
    def _condition_slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", str(value).casefold()).strip("_")

    @staticmethod
    def _selected_range_value(match: re.Match[str], use_max_value: bool) -> float:
        key = "max" if use_max_value else "min"
        return float(match.group(key).replace(",", ""))

    @staticmethod
    def _effect(
        stat: StatId,
        value: float,
        source: str,
        *,
        operation: EffectOperation = EffectOperation.ADD,
        unit: EffectUnit = EffectUnit.FLAT,
        condition: str | None = None,
    ) -> Effect:
        return Effect(
            operation=operation,
            value=value,
            source=source,
            stat=stat,
            kind=EffectKind.STAT,
            unit=unit,
            condition=condition,
        )
