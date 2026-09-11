from __future__ import annotations

"""Extreme-only resource projection for reviewed gear-set descriptions.

The shared ``GearSetEffectResolver`` deliberately stays conservative across every
feature.  Extreme max-resource search needs a slightly wider reviewed vocabulary
for gear bonuses whose resource math is explicit even when the set also contains
unrelated mechanics.  This adapter delegates to the shared resolver first and
adds only narrowly reviewed resource patterns.

Some reviewed stack mechanics are represented at their explicit extrema with a
condition marker.  That is sufficient for denominator relevance, but the marker
must still be proven by a runtime/structural scorer before the effect is executable.
"""

import re

from minmax.effect_kinds import EffectKind
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.gear_set_effect_resolver import GearSetEffectResolver
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId


class ExtremeGearSetResourceEffectResolver:
    """Resolve reviewed finite max-resource gear effects without guessing."""

    _RANGE = r"(?P<min>\d[\d,]*)\s*-\s*(?P<max>\d[\d,]*)"

    def __init__(self, base: GearSetEffectResolver | None = None) -> None:
        self.base = base or GearSetEffectResolver()

    @staticmethod
    def _value(match: re.Match[str], use_max_value: bool) -> float:
        key = "max" if use_max_value else "min"
        return float(match.group(key).replace(",", ""))

    @staticmethod
    def _effect(
        stat: StatId,
        value: float,
        source: str,
        *,
        condition: str | None = None,
        operation: EffectOperation = EffectOperation.ADD,
        unit: EffectUnit = EffectUnit.FLAT,
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

    def resolve(
        self,
        bonus: GearSetBonus,
        *,
        use_max_value: bool = True,
        source: str | None = None,
    ) -> list[Effect]:
        shared = self.base.resolve(
            bonus,
            use_max_value=use_max_value,
            source=source,
        )
        if shared:
            return shared

        text = self.base._clean_description(str(bonus.description or ""))
        if not text:
            return []
        source_text = source or f"Gear set bonus ({bonus.piece_count} items)"

        # Ebon Armory style persistent self/group Max Health bonus.
        match = re.fullmatch(
            rf"Increases Max Health by {self._RANGE} for you and up to \d+ other group members "
            r"within \d+ meters of you\. This bonus persists through death\.?",
            text,
            re.IGNORECASE,
        )
        if match:
            return [
                self._effect(
                    StatId.MAX_HEALTH,
                    self._value(match, use_max_value),
                    source_text,
                )
            ]

        # Xoryn's Masterpiece style dual-resource persistent aura.
        match = re.fullmatch(
            r"Increases Max Magicka and Max Stamina by (?P<value>\d[\d,]*) for you and up to "
            r"\d+ other group members within \d+ meters of you\. This bonus persists through death\.?",
            text,
            re.IGNORECASE,
        )
        if match:
            value = float(match.group("value").replace(",", ""))
            return [
                self._effect(StatId.MAX_MAGICKA, value, source_text),
                self._effect(StatId.MAX_STAMINA, value, source_text),
            ]

        # Green Pact.
        match = re.fullmatch(
            rf"While you have a food buff active, your Max Health is increased by {self._RANGE} "
            r"and Health Recovery by (?P<rec_min>\d[\d,]*)\s*-\s*(?P<rec_max>\d[\d,]*)\.?",
            text,
            re.IGNORECASE,
        )
        if match:
            recovery_key = "rec_max" if use_max_value else "rec_min"
            return [
                self._effect(
                    StatId.MAX_HEALTH,
                    self._value(match, use_max_value),
                    source_text,
                    condition="food_buff_active",
                ),
                self._effect(
                    StatId.HEALTH_RECOVERY,
                    float(match.group(recovery_key).replace(",", "")),
                    source_text,
                    condition="food_buff_active",
                ),
            ]

        # Bright-Throat's Boast.
        match = re.fullmatch(
            rf"While you have a drink buff active, your Max Magicka is increased by {self._RANGE} "
            r"and Magicka Recovery by (?P<rec_min>\d[\d,]*)\s*-\s*(?P<rec_max>\d[\d,]*)\.?",
            text,
            re.IGNORECASE,
        )
        if match:
            recovery_key = "rec_max" if use_max_value else "rec_min"
            return [
                self._effect(
                    StatId.MAX_MAGICKA,
                    self._value(match, use_max_value),
                    source_text,
                    condition="drink_buff_active",
                ),
                self._effect(
                    StatId.MAGICKA_RECOVERY,
                    float(match.group(recovery_key).replace(",", "")),
                    source_text,
                    condition="drink_buff_active",
                ),
            ]

        # Bone Pirate's Tatters.
        match = re.fullmatch(
            rf"While you have a drink buff active, your Max Stamina is increased by {self._RANGE} "
            r"and Stamina Recovery by (?P<rec_min>\d[\d,]*)\s*-\s*(?P<rec_max>\d[\d,]*)\.?",
            text,
            re.IGNORECASE,
        )
        if match:
            recovery_key = "rec_max" if use_max_value else "rec_min"
            return [
                self._effect(
                    StatId.MAX_STAMINA,
                    self._value(match, use_max_value),
                    source_text,
                    condition="drink_buff_active",
                ),
                self._effect(
                    StatId.STAMINA_RECOVERY,
                    float(match.group(recovery_key).replace(",", "")),
                    source_text,
                    condition="drink_buff_active",
                ),
            ]

        # Necropotence.
        match = re.fullmatch(
            rf"While you have a pet active, your Max Magicka is increased by {self._RANGE}\.?",
            text,
            re.IGNORECASE,
        )
        if match:
            return [
                self._effect(
                    StatId.MAX_MAGICKA,
                    self._value(match, use_max_value),
                    source_text,
                    condition="pet_active",
                )
            ]

        # Shapeshifter's Chain.  Ability-cost reduction is intentionally outside
        # max-resource projection; the transformed resource bonus is explicit.
        match = re.fullmatch(
            r"Reduce the cost of your Transformation Ultimate and Werewolf abilities by \d+(?:\.\d+)?%\. "
            r"While transformed, increase your Maximum Health, Stamina, and Magicka by "
            r"(?P<value>\d[\d,]*)\.?",
            text,
            re.IGNORECASE,
        )
        if match:
            value = float(match.group("value").replace(",", ""))
            return [
                self._effect(StatId.MAX_HEALTH, value, source_text, condition="transformed"),
                self._effect(StatId.MAX_STAMINA, value, source_text, condition="transformed"),
                self._effect(StatId.MAX_MAGICKA, value, source_text, condition="transformed"),
            ]

        # Armor Master: preserve the 5% Max Health mechanic explicitly.  Percentage
        # stacking/reference semantics remain an executable Extreme blocker until
        # the canonical sheet layer proves the correct base.
        match = re.fullmatch(
            r"While you have an Armor ability slotted, your Max Health is increased by "
            r"(?P<value>\d+(?:\.\d+)?)%\. When you use an Armor ability while in combat, "
            r"your Physical and Spell Resistance is increased by \d[\d,]*\s*-\s*\d[\d,]* for \d+ seconds?\.?",
            text,
            re.IGNORECASE,
        )
        if match:
            return [
                self._effect(
                    StatId.MAX_HEALTH,
                    float(match.group("value")),
                    source_text,
                    condition="armor_ability_slotted",
                    operation=EffectOperation.ADD_PERCENT,
                    unit=EffectUnit.PERCENT,
                )
            ]

        # Death Dealer's Fete: denominator relevance uses the explicit maximum
        # stack state (30 * 88). Runtime must still prove the stack count.
        match = re.fullmatch(
            r"Gain a persistent stack of Escalating Fete every (?P<gain_seconds>\d+) seconds you are in combat, "
            r"up to (?P<max_stacks>\d+) stacks max\. Each stack of Escalating Fete increases your "
            r"Maximum Stamina, Health, and Magicka by (?P<per_stack>\d[\d,]*)\. You lose a stack of "
            r"Escalating Fete every (?P<loss_seconds>\d+) seconds you are out of combat\.?",
            text,
            re.IGNORECASE,
        )
        if match:
            maximum = int(match.group("max_stacks")) * float(match.group("per_stack").replace(",", ""))
            condition = f"escalating_fete_stacks:{match.group('max_stacks')}"
            return [
                self._effect(StatId.MAX_HEALTH, maximum, source_text, condition=condition),
                self._effect(StatId.MAX_MAGICKA, maximum, source_text, condition=condition),
                self._effect(StatId.MAX_STAMINA, maximum, source_text, condition=condition),
            ]

        # Prowler's Talisman: only the critical-damage stack branch changes max
        # resources. Represent its explicit cap for relevance; runtime owns stacks.
        match = re.fullmatch(
            r"While Battle Spirit is inactive, bracing while crouching turns you invisible for \d+ seconds\. "
            r"This can occur once every \d+ seconds\. Increase your chances of successfully Pickpocketing by \d+%\. "
            r"On dealing Critical Damage, increase your Max Magicka and Max Stamina for \d+ seconds, "
            r"up to (?P<resource_cap>\d[\d,]*) at (?P<max_stacks>\d+) stacks\. On dealing non-Critical Damage, "
            r"increase your Health, Magicka, and Stamina Recovery for \d+ seconds, up to \d[\d,]* at \d+ stacks\. "
            r"Either effect can occur up to once every \d+ second\. Talisman upgrades: \d+\.?",
            text,
            re.IGNORECASE,
        )
        if match:
            value = float(match.group("resource_cap").replace(",", ""))
            condition = f"prowlers_talisman_critical_stacks:{match.group('max_stacks')}"
            return [
                self._effect(StatId.MAX_MAGICKA, value, source_text, condition=condition),
                self._effect(StatId.MAX_STAMINA, value, source_text, condition=condition),
            ]

        # Thrassian Stranglers: every stack is strictly harmful to Max Health.
        # The maximum stack state makes the sign explicit for denominator pruning;
        # runtime still owns the actual current stack count and reset conditions.
        match = re.fullmatch(
            r"Killing an enemy grants you a stack of Sload's Call for \d+ hour, up to a maximum of "
            r"(?P<max_stacks>\d+) stacks\. Each stack increases your Weapon and Spell Damage by \d[\d,]*, "
            r"reduces your Maximum Health by\s*(?P<per_stack>\d[\d,]*), and reduces effectiveness of your "
            r"damage shields by \d+%\. Sload's Call is lost if you remove Thrassian Stranglers, go invisible, or crouch\.?",
            text,
            re.IGNORECASE,
        )
        if match:
            maximum_loss = int(match.group("max_stacks")) * float(match.group("per_stack").replace(",", ""))
            return [
                self._effect(
                    StatId.MAX_HEALTH,
                    -maximum_loss,
                    source_text,
                    condition=f"sloads_call_stacks:{match.group('max_stacks')}",
                )
            ]

        return []


__all__ = ["ExtremeGearSetResourceEffectResolver"]
