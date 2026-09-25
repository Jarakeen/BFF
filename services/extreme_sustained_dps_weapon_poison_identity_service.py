from __future__ import annotations

"""Resolve saved crafted weapon-poison labels to source-backed possibility evidence.

UESP Alchemy Poison variants are imported into effect_variant.raw_json. Each per-effect
page retains Poison tier rows containing crafted item names plus base/triple duration
alternatives. The same displayed poison item name can be produced by multiple formulas
with different secondary effects, so a saved item label proves a possibility universe,
not the exact effect set on the selected bottle.

This service is intentionally read-only and fail-closed for exact Objective #32 use.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonPossibleEffect:
    effect_name: str
    base_duration_seconds: float
    triple_duration_seconds: float | None = None
    solvent: str | None = None
    level: int | None = None


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonItemEvidence:
    poison_id: str
    possible_effects: tuple[ExtremeSustainedDPSWeaponPoisonPossibleEffect, ...]
    source_evidence_complete: bool
    exact_selection_proven: bool
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return bool(
            self.possible_effects
            and self.source_evidence_complete
            and self.exact_selection_proven
            and not self.unresolved
        )


class ExtremeSustainedDPSWeaponPoisonItemEvidenceService:
    """Read possible Poison effects/duration alternatives from imported Alchemy evidence."""

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

    def resolve(self, poison_id: str) -> ExtremeSustainedDPSWeaponPoisonItemEvidence:
        selected = " ".join(str(poison_id or "").strip().split())
        if not selected:
            return ExtremeSustainedDPSWeaponPoisonItemEvidence(
                poison_id="",
                possible_effects=(),
                source_evidence_complete=False,
                exact_selection_proven=False,
                unresolved=("weapon-poison item evidence requires a poison item name",),
            )
        if not self.database_path.exists():
            return ExtremeSustainedDPSWeaponPoisonItemEvidence(
                poison_id=selected,
                possible_effects=(),
                source_evidence_complete=False,
                exact_selection_proven=False,
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
                    return ExtremeSustainedDPSWeaponPoisonItemEvidence(
                        poison_id=selected,
                        possible_effects=(),
                        source_evidence_complete=False,
                        exact_selection_proven=False,
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
                    return ExtremeSustainedDPSWeaponPoisonItemEvidence(
                        poison_id=selected,
                        possible_effects=(),
                        source_evidence_complete=False,
                        exact_selection_proven=False,
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
            return ExtremeSustainedDPSWeaponPoisonItemEvidence(
                poison_id=selected,
                possible_effects=(),
                source_evidence_complete=False,
                exact_selection_proven=False,
                unresolved=(f"Alchemy poison catalog unreadable: {exc}",),
            )

        matches: dict[str, ExtremeSustainedDPSWeaponPoisonPossibleEffect] = {}
        source_errors: list[str] = []
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
                    source_errors.append(
                        f"{selected}: {effect_name} poison tier has no valid base duration"
                    )
                    continue

                identity = ExtremeSustainedDPSWeaponPoisonPossibleEffect(
                    effect_name=effect_name,
                    base_duration_seconds=duration,
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
                    source_errors.append(
                        f"{selected}: conflicting imported poison tier evidence "
                        f"for {effect_name}"
                    )
                    continue
                matches[key] = identity

        possible_effects = tuple(
            sorted(
                matches.values(),
                key=lambda row: self._norm(row.effect_name),
            )
        )
        if not possible_effects and not source_errors:
            source_errors.append(
                f"Crafted weapon poison not found in canonical Alchemy Poison tiers: {selected}"
            )

        source_complete = bool(possible_effects) and not source_errors
        unresolved = list(source_errors)
        if source_complete:
            unresolved.append(
                f"{selected}: saved poison item label proves possible effects but not "
                "the exact crafted formula/effect set or dilution duration"
            )

        return ExtremeSustainedDPSWeaponPoisonItemEvidence(
            poison_id=selected,
            possible_effects=possible_effects,
            source_evidence_complete=source_complete,
            exact_selection_proven=False,
            evidence=(
                f"Canonical Alchemy Poison variants inspected: {len(rows)}",
                f"Poison tier rows matching {selected}: {matched_rows}",
                f"Distinct possible poison effect identities: {len(possible_effects)}",
                (
                    f"Malformed Alchemy Poison payloads ignored: {malformed_payloads}"
                    if malformed_payloads
                    else "Malformed Alchemy Poison payloads ignored: 0"
                ),
                "Imported Poison tier rows establish an item-label possibility universe only; exact formula/effect-set and base-versus-triple dilution require separate provenance.",
            ),
            unresolved=tuple(
                dict.fromkeys(row for row in unresolved if str(row).strip())
            ),
        )


# Transitional aliases keep any very recent callers from breaking while making the
# corrected possibility semantics explicit to new code.
ExtremeSustainedDPSWeaponPoisonAlchemyEffectIdentity = (
    ExtremeSustainedDPSWeaponPoisonPossibleEffect
)
ExtremeSustainedDPSWeaponPoisonIdentityResolution = (
    ExtremeSustainedDPSWeaponPoisonItemEvidence
)
ExtremeSustainedDPSWeaponPoisonIdentityService = (
    ExtremeSustainedDPSWeaponPoisonItemEvidenceService
)


__all__ = [
    "ExtremeSustainedDPSWeaponPoisonPossibleEffect",
    "ExtremeSustainedDPSWeaponPoisonItemEvidence",
    "ExtremeSustainedDPSWeaponPoisonItemEvidenceService",
    "ExtremeSustainedDPSWeaponPoisonAlchemyEffectIdentity",
    "ExtremeSustainedDPSWeaponPoisonIdentityResolution",
    "ExtremeSustainedDPSWeaponPoisonIdentityService",
]
