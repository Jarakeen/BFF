import re

from .effect_kinds import EffectKind
from .effects import Effect, EffectOperation, EffectUnit
from .stat_ids import StatId


class EffectResolver:
    """Resolve simple self-applied ESO effect descriptions into engine Effects.

    This intentionally handles only direct character-stat effects.
    Conditional, target-based, damage, proc, and resource effects belong
    to the combat/rule effect layers.
    """

    _PATTERNS = (
        # ============================================================
        # Combined percentage stats
        # ============================================================

        (
            re.compile(
                r"increases your weapon and spell damage by ([\d.]+)%",
                re.IGNORECASE,
            ),
            (StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE),
            EffectOperation.ADD_PERCENT,
            EffectUnit.PERCENT,
        ),

        # ============================================================
        # Single percentage stats
        # ============================================================

        (
            re.compile(
                r"increases weapon damage by ([\d.]+)%",
                re.IGNORECASE,
            ),
            (StatId.WEAPON_DAMAGE,),
            EffectOperation.ADD_PERCENT,
            EffectUnit.PERCENT,
        ),
        (
            re.compile(
                r"increases spell damage by ([\d.]+)%",
                re.IGNORECASE,
            ),
            (StatId.SPELL_DAMAGE,),
            EffectOperation.ADD_PERCENT,
            EffectUnit.PERCENT,
        ),
        (
            re.compile(
                r"increases maximum health by ([\d.]+)%",
                re.IGNORECASE,
            ),
            (StatId.MAX_HEALTH,),
            EffectOperation.ADD_PERCENT,
            EffectUnit.PERCENT,
        ),
        (
            re.compile(
                r"increases maximum magicka by ([\d.]+)%",
                re.IGNORECASE,
            ),
            (StatId.MAX_MAGICKA,),
            EffectOperation.ADD_PERCENT,
            EffectUnit.PERCENT,
        ),
        (
            re.compile(
                r"increases maximum stamina by ([\d.]+)%",
                re.IGNORECASE,
            ),
            (StatId.MAX_STAMINA,),
            EffectOperation.ADD_PERCENT,
            EffectUnit.PERCENT,
        ),
        (
            re.compile(
                r"increases health recovery by ([\d.]+)%",
                re.IGNORECASE,
            ),
            (StatId.HEALTH_RECOVERY,),
            EffectOperation.ADD_PERCENT,
            EffectUnit.PERCENT,
        ),
        (
            re.compile(
                r"increases magicka recovery by ([\d.]+)%",
                re.IGNORECASE,
            ),
            (StatId.MAGICKA_RECOVERY,),
            EffectOperation.ADD_PERCENT,
            EffectUnit.PERCENT,
        ),
        (
            re.compile(
                r"increases stamina recovery by ([\d.]+)%",
                re.IGNORECASE,
            ),
            (StatId.STAMINA_RECOVERY,),
            EffectOperation.ADD_PERCENT,
            EffectUnit.PERCENT,
        ),
        (
            re.compile(
                r"increases critical damage done by ([\d.]+)%",
                re.IGNORECASE,
            ),
            (StatId.CRITICAL_DAMAGE,),
            EffectOperation.ADD_PERCENT,
            EffectUnit.PERCENT,
        ),
        (
            re.compile(
                r"increases healing done by ([\d.]+)%",
                re.IGNORECASE,
            ),
            (StatId.HEALING_DONE,),
            EffectOperation.ADD_PERCENT,
            EffectUnit.PERCENT,
        ),

        # ============================================================
        # Combined flat stats
        # ============================================================

        (
            re.compile(
                r"increase your weapon and spell damage by ([\d,]+)(?![\d%])",
                re.IGNORECASE,
            ),
            (StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE),
            EffectOperation.ADD,
            EffectUnit.FLAT,
        ),
        (
            re.compile(
                r"increases (?:physical and spell resistance) by ([\d,]+)(?![\d%])",
                re.IGNORECASE,
            ),
            (StatId.PHYSICAL_RESISTANCE, StatId.SPELL_RESISTANCE),
            EffectOperation.ADD,
            EffectUnit.FLAT,
        ),

        # ============================================================
        # Single flat stats
        # ============================================================

        (
            re.compile(
                r"increases weapon damage by ([\d,]+)(?![\d%])",
                re.IGNORECASE,
            ),
            (StatId.WEAPON_DAMAGE,),
            EffectOperation.ADD,
            EffectUnit.FLAT,
        ),
        (
            re.compile(
                r"increases spell damage by ([\d,]+)(?![\d%])",
                re.IGNORECASE,
            ),
            (StatId.SPELL_DAMAGE,),
            EffectOperation.ADD,
            EffectUnit.FLAT,
        ),
        (
            re.compile(
                r"increases maximum health by ([\d,]+)(?![\d%])",
                re.IGNORECASE,
            ),
            (StatId.MAX_HEALTH,),
            EffectOperation.ADD,
            EffectUnit.FLAT,
        ),
        (
            re.compile(
                r"increases maximum magicka by ([\d,]+)(?![\d%])",
                re.IGNORECASE,
            ),
            (StatId.MAX_MAGICKA,),
            EffectOperation.ADD,
            EffectUnit.FLAT,
        ),
        (
            re.compile(
                r"increases maximum stamina by ([\d,]+)(?![\d%])",
                re.IGNORECASE,
            ),
            (StatId.MAX_STAMINA,),
            EffectOperation.ADD,
            EffectUnit.FLAT,
        ),
        (
            re.compile(
                r"increases health recovery by ([\d,]+)(?![\d%])",
                re.IGNORECASE,
            ),
            (StatId.HEALTH_RECOVERY,),
            EffectOperation.ADD,
            EffectUnit.FLAT,
        ),
        (
            re.compile(
                r"increases magicka recovery by ([\d,]+)(?![\d%])",
                re.IGNORECASE,
            ),
            (StatId.MAGICKA_RECOVERY,),
            EffectOperation.ADD,
            EffectUnit.FLAT,
        ),
        (
            re.compile(
                r"increases stamina recovery by ([\d,]+)(?![\d%])",
                re.IGNORECASE,
            ),
            (StatId.STAMINA_RECOVERY,),
            EffectOperation.ADD,
            EffectUnit.FLAT,
        ),
        (
            re.compile(
                r"increases spell critical by ([\d,]+)(?![\d%])",
                re.IGNORECASE,
            ),
            (StatId.SPELL_CRITICAL,),
            EffectOperation.ADD,
            EffectUnit.FLAT,
        ),
        (
            re.compile(
                r"increases weapon critical by ([\d,]+)(?![\d%])",
                re.IGNORECASE,
            ),
            (StatId.WEAPON_CRITICAL,),
            EffectOperation.ADD,
            EffectUnit.FLAT,
        ),
    )

    def resolve(
        self,
        *,
        name: str,
        description: str,
        category: str = "buff",
    ) -> list[Effect]:
        """Resolve a database effect variant into zero or more Effects."""

        text = " ".join(description.split())

        if not text:
            return []

        # Never turn target/debuff mechanics into self-stat effects.
        if category.lower() == "debuff" or "target" in text.lower():
            return []

        for pattern, stats, operation, unit in self._PATTERNS:
            match = pattern.search(text)

            if not match:
                continue

            value = float(match.group(1).replace(",", ""))

            return [
                Effect(
                    kind=EffectKind.STAT,
                    stat=stat,
                    operation=operation,
                    value=value,
                    source=name,
                    unit=unit,
                )
                for stat in stats
            ]

        return []
