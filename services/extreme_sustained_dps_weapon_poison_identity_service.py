from __future__ import annotations

"""Resolve saved crafted weapon-poison names to canonical alchemy effect identities.

UESP alchemy Poison variants are imported into effect_variant.raw_json. Each effect
page retains poison tier rows containing the crafted item name and that effect's
duration. Matching the saved poison item name across all Poison variants therefore
recovers the complete effect-identity set for multi-effect poisons without a manual
name map. Magnitude/application math remains downstream.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonAlchemyEffectIdentity:
    effect_name: str
    duration_seconds: float
    triple_duration_seconds: float | None = None
    solvent: str | None = None
    level: int | None = None


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonIdentityResolution:
    poison_id: str
    effects: tuple[ExtremeSustainedDPSWeaponPoisonAlchemyEffectIdentity, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return bool(self.effects) and not self.unresolved


class ExtremeSustainedDPSWeaponPoisonIdentityService:
    """Read canonical Poison effect identity/duration from imported alchemy evidence."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def _norm(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @staticmethod
    def _float(value: object) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _int(value: object) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def resolve(
        self,
        poison_id: str,
    ) -> ExtremeSustainedDPSWeaponPoisonIdentityResolution:
        selected = " ".join(str(poison_id or "").strip().split())
        if not selected:
            return ExtremeSustainedDPSWeaponPoisonIdentityResolution(
                poison_id="",
                effects=(),
                unresolved=("weapon-poison identity resolution requires a poison item name",),
            )
        if not self.database_path.exists():
            return ExtremeSustainedDPSWeaponPoisonIdentityResolution(
                poison_id=selected,
                effects=(),
                unresolved=(f"Alchemy database missing: {self.database_path}",),
            )

        try:
            with sqlite3.connect(self.database_path) as db:
                tables = {
                    str(row[0])
                    for row in db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                if not {"effect", "effect_variant"}.issubset(tables):
                    return ExtremeSustainedDPSWeaponPoisonIdentityResolution(
                        poison_id=selected,
                        effects=(),
                        unresolved=(
                            "Alchemy database is missing effect/effect_variant tables",
                        ),
                    )
                columns = {
                    str(row[1])
                    for row in db.execute(
                        "PRAGMA table_info(effect_variant)"
                    ).fetchall()
                }
                if "raw_json" not in columns:
                    return ExtremeSustainedDPSWeaponPoisonIdentityResolution(
                        poison_id=selected,
                        effects=(),
                        unresolved=(
                            "Alchemy database effect_variant table has no raw_json source payload",
                        ),
                    )

                rows = db.execute(
                    """
                    SELECT e.name, ev.raw_json
                    FROM effect e
                    JOIN effect_variant ev ON ev.effect_id = e.id
                    WHERE lower(trim(COALESCE(ev.type, ''))) = 'poison'
                      AND trim(COALESCE(ev.raw_json, '')) <> ''
                    ORDER BY e.id, ev.id
                    """
                ).fetchall()
        except sqlite3.Error as exc:
            return ExtremeSustainedDPSWeaponPoisonIdentityResolution(
                poison_id=selected,
                effects=(),
                unresolved=(f"Alchemy poison catalog unreadable: {exc}",),
            )

        matches: dict[str, ExtremeSustainedDPSWeaponPoisonAlchemyEffectIdentity] = {}
        unresolved: list[str] = []
        malformed_payloads = 0
        matched_rows = 0

        for db_effect_name, raw_json in rows:
            try:
                payload = json.loads(str(raw_json))
            except (TypeError, ValueError, json.JSONDecodeError):
                malformed_payloads += 1
                continue
            if not isinstance(payload, dict):
                malformed_payloads += 1
                continue

            effect_name = str(
                payload.get("effect_name") or db_effect_name or ""
            ).strip()
            tiers = payload.get("tiers")
            if not effect_name or not isinstance(tiers, list):
                continue

            for tier in tiers:
                if not isinstance(tier, dict):
                    continue
                if self._norm(tier.get("name")) != self._norm(selected):
                    continue
                matched_rows += 1
                duration = self._float(tier.get("duration"))
                if duration is None or duration < 0.0:
                    unresolved.append(
                        f"{selected}: {effect_name} poison tier has no valid duration"
                    )
                    continue

                identity = ExtremeSustainedDPSWeaponPoisonAlchemyEffectIdentity(
                    effect_name=effect_name,
                    duration_seconds=duration,
                    triple_duration_seconds=self._float(
                        tier.get("triple_duration")
                    ),
                    solvent=(
                        str(tier.get("solvent") or "").strip() or None
                    ),
                    level=self._int(tier.get("level")),
                )
                key = self._norm(effect_name)
                existing = matches.get(key)
                if existing is not None and existing != identity:
                    unresolved.append(
                        f"{selected}: conflicting imported poison tier evidence "
                        f"for {effect_name}"
                    )
                    continue
                matches[key] = identity

        effects = tuple(
            sorted(
                matches.values(),
                key=lambda row: self._norm(row.effect_name),
            )
        )
        if not effects and not unresolved:
            unresolved.append(
                f"Crafted weapon poison not found in canonical alchemy Poison tiers: {selected}"
            )

        return ExtremeSustainedDPSWeaponPoisonIdentityResolution(
            poison_id=selected,
            effects=effects,
            evidence=(
                f"Canonical alchemy Poison variants inspected: {len(rows)}",
                f"Poison tier rows matching {selected}: {matched_rows}",
                f"Distinct poison effect identities resolved: {len(effects)}",
                (
                    f"Malformed alchemy Poison payloads ignored: {malformed_payloads}"
                    if malformed_payloads
                    else "Malformed alchemy Poison payloads ignored: 0"
                ),
                "Effect identity and duration come from imported UESP Poison tier rows; magnitude/application remain downstream.",
            ),
            unresolved=tuple(
                dict.fromkeys(row for row in unresolved if str(row).strip())
            ),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponPoisonAlchemyEffectIdentity",
    "ExtremeSustainedDPSWeaponPoisonIdentityResolution",
    "ExtremeSustainedDPSWeaponPoisonIdentityService",
]
