from __future__ import annotations

"""Source-backed potion-tier evidence for temporal Alchemy mechanics.

The processed UESP corpus contains potion and poison tier rows plus occasional
concatenated table-header artifacts. This repository exposes only usable potion
rows and preserves both the ordinary and all-three-reagent duration columns.
It does not apply Medicinal Use, cooldowns, or active combat buffs.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED = ROOT / "data" / "processed" / "alchemy_effects.json"

_RESTORE_TRAITS = frozenset({"Restore Health", "Restore Magicka", "Restore Stamina"})


def _clean(value: Any) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _float(value: Any) -> float | None:
    try:
        return float(_clean(value))
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class PotionTierEvidence:
    effect_name: str
    solvent: str
    level: int
    potion_name: str
    magnitude: float | None
    duration: float | None
    triple_duration: float | None
    raw_values: tuple[str, ...]


class AlchemyPotionTierRepository:
    """Read normalized UESP potion-tier rows without inventing mechanics."""

    def __init__(self, processed_path: str | Path = DEFAULT_PROCESSED) -> None:
        self.processed_path = Path(processed_path)

    def _effects(self) -> dict[str, dict[str, Any]]:
        if not self.processed_path.exists():
            return {}
        try:
            payload = json.loads(self.processed_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        rows = payload.get("effects", []) if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            return {}
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = _clean(row.get("effect_name") or row.get("name"))
            if name:
                result[name.casefold()] = row
        return result

    @staticmethod
    def _parse_row(effect_name: str, row: dict[str, Any]) -> PotionTierEvidence | None:
        solvent = _clean(row.get("solvent"))
        potion_name = _clean(row.get("name"))
        level_text = _clean(row.get("level"))

        # V3's generic table parser can emit one concatenated header/body row,
        # and some historical records include poison rows in potion_tiers.
        # Both are source artifacts, not potion tiers.
        try:
            level = int(level_text)
        except ValueError:
            return None
        if not solvent or not potion_name or "poison" in potion_name.casefold():
            return None

        values = row.get("values", [])
        if not isinstance(values, list):
            values = [values]
        raw_values = tuple(_clean(value) for value in values if _clean(value))

        if effect_name in _RESTORE_TRAITS:
            if len(raw_values) < 3:
                return None
            magnitude = _float(raw_values[0])
            duration = _float(raw_values[1])
            triple_duration = _float(raw_values[2])
        else:
            if len(raw_values) < 2:
                return None
            magnitude = None
            duration = _float(raw_values[0])
            triple_duration = _float(raw_values[1])

        if duration is None or triple_duration is None:
            return None
        if effect_name in _RESTORE_TRAITS and magnitude is None:
            return None

        return PotionTierEvidence(
            effect_name=effect_name,
            solvent=solvent,
            level=level,
            potion_name=potion_name,
            magnitude=magnitude,
            duration=duration,
            triple_duration=triple_duration,
            raw_values=raw_values,
        )

    def tiers(self, effect_name: str) -> tuple[PotionTierEvidence, ...]:
        clean_name = _clean(effect_name)
        if not clean_name:
            return ()
        effect = self._effects().get(clean_name.casefold())
        if effect is None:
            return ()
        rows = effect.get("potion_tiers", [])
        if not isinstance(rows, list):
            return ()
        parsed = [
            tier
            for row in rows
            if isinstance(row, dict)
            for tier in [self._parse_row(clean_name, row)]
            if tier is not None
        ]
        return tuple(parsed)

    def max_tier(self, effect_name: str) -> PotionTierEvidence | None:
        tiers = self.tiers(effect_name)
        if not tiers:
            return None
        return max(tiers, key=lambda tier: (tier.level, tier.potion_name.casefold()))
