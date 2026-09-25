from __future__ import annotations

"""Canonical read-only crafted weapon-poison formula availability.

This repository deliberately queries only imported Alchemy Poison variants. It
reuses the shared AlchemyFormulaCatalog parser, but it does not borrow potion variant
rows as proof that a formula belongs in the poison selection denominator.
"""

import json
from pathlib import Path
import sqlite3

from minmax.alchemy_formula_catalog import AlchemyFormulaCatalog
from minmax.combat_effect_semantics import GameUpdate, normalize_game_update


class WeaponPoisonAvailabilityRepository:
    """Expose source-backed canonical Alchemy formulas from Poison variants only."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        game_update: GameUpdate | str = GameUpdate.U50,
    ) -> None:
        self.database_path = Path(database_path)
        self.game_update = normalize_game_update(game_update)
        self._catalog_cache: AlchemyFormulaCatalog | None = None

    def _database_payload(
        self,
    ) -> tuple[dict[str, object] | None, tuple[str, ...]]:
        if not self.database_path.exists():
            return None, (f"Alchemy database missing: {self.database_path}",)

        try:
            with sqlite3.connect(self.database_path) as db:
                tables = {
                    str(row[0])
                    for row in db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                if not {"effect", "effect_variant"}.issubset(tables):
                    return None, (
                        "Alchemy database is missing effect/effect_variant tables",
                    )

                columns = {
                    str(row[1])
                    for row in db.execute(
                        "PRAGMA table_info(effect_variant)"
                    ).fetchall()
                }
                if "raw_json" not in columns:
                    return None, (
                        "Alchemy database effect_variant table has no raw_json source payload",
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
            return None, (f"Alchemy poison catalog unreadable: {exc}",)

        effects: list[dict[str, object]] = []
        malformed: list[str] = []
        for effect_name, raw_json in rows:
            try:
                payload = json.loads(str(raw_json))
            except (TypeError, ValueError, json.JSONDecodeError):
                malformed.append(str(effect_name or "unknown"))
                continue
            if not isinstance(payload, dict):
                malformed.append(str(effect_name or "unknown"))
                continue

            variant = str(payload.get("variant") or "").strip().casefold()
            if variant and variant != "poison":
                malformed.append(str(effect_name or "unknown"))
                continue

            formulas = payload.get("formulas")
            if not isinstance(formulas, list) or not formulas:
                continue

            name = str(
                payload.get("effect_name") or effect_name or ""
            ).strip()
            if not name:
                malformed.append(str(effect_name or "unknown"))
                continue
            effects.append(
                {
                    "effect_name": name,
                    "source_files": payload.get("source_files", []) or [],
                    "formulas": formulas,
                }
            )

        if not effects:
            detail = ""
            if malformed:
                detail = (
                    "; malformed Poison payload(s): "
                    + ", ".join(dict.fromkeys(malformed))
                )
            return None, (
                "Alchemy database contains no reusable Poison formula payloads"
                + detail,
            )

        unresolved: list[str] = []
        if malformed:
            unresolved.append(
                "Malformed Poison formula payload(s) rejected: "
                + ", ".join(dict.fromkeys(malformed))
            )
        return {"effects": effects}, tuple(unresolved)

    def catalog(self) -> AlchemyFormulaCatalog:
        cached = self._catalog_cache
        if cached is not None:
            return cached

        payload, source_unresolved = self._database_payload()
        if payload is None:
            result = AlchemyFormulaCatalog(
                formulas=(),
                game_update=self.game_update,
                unresolved=source_unresolved,
            )
            self._catalog_cache = result
            return result

        parsed = AlchemyFormulaCatalog.from_processed_payload(
            payload,
            game_update=self.game_update,
            allow_legacy_alias=self.game_update is GameUpdate.U51,
        )
        result = AlchemyFormulaCatalog(
            formulas=tuple(parsed.formulas),
            game_update=parsed.game_update,
            unresolved=tuple(
                dict.fromkeys(
                    (
                        *tuple(source_unresolved),
                        *tuple(parsed.unresolved),
                    )
                )
            ),
        )
        self._catalog_cache = result
        return result


__all__ = ["WeaponPoisonAvailabilityRepository"]
