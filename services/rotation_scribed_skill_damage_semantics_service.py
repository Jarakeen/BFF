from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from minmax.damage_done import DamageDoneModifiers
from services.scribing_catalog import result_identity


@dataclass(frozen=True)
class RotationScribedSkillDamageSemantics:
    """Reviewed DD-facing semantics for one verified scribed result name."""

    result_name: str
    grimoire: str
    focus: str
    deals_direct_damage_on_activation: bool
    persistent_toggle: bool
    active_damage_done: DamageDoneModifiers
    source: str


class RotationScribedSkillDamageSemanticsService:
    """Resolve only explicitly reviewed scribed DD semantics.

    Result-name identity remains owned by ``services.scribing_catalog``. Reviewed
    rotation-facing semantics are loaded from versioned repository data instead of
    being embedded in source. Unknown or unreviewed scribed results return ``None``
    and remain fail-closed in their ordinary canonical skill path.
    """

    SCHEMA_VERSION = 1

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = (
            Path(path)
            if path is not None
            else Path(__file__).resolve().parents[1]
            / "data"
            / "rotation_scribed_skill_damage_semantics.json"
        )
        self._by_identity = self._load()

    def resolve(self, result_name: str) -> RotationScribedSkillDamageSemantics | None:
        identity = result_identity(result_name)
        if identity is None:
            return None
        return self._by_identity.get(identity)

    def _load(self) -> dict[tuple[str, str], RotationScribedSkillDamageSemantics]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("scribed damage semantics registry must be a JSON object")
        if payload.get("schema_version") != self.SCHEMA_VERSION:
            raise ValueError("scribed damage semantics registry schema_version must be 1")
        rows = payload.get("entries", [])
        if not isinstance(rows, list):
            raise ValueError("scribed damage semantics registry entries must be a list")

        by_identity: dict[tuple[str, str], RotationScribedSkillDamageSemantics] = {}
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError(
                    f"scribed damage semantics registry entry {index} must be an object"
                )
            try:
                result_name = str(row["result_name"]).strip()
                grimoire = str(row["grimoire"]).strip()
                focus = str(row["focus"]).strip()
                source = str(row["source"]).strip()
                modifiers = row.get("active_damage_done", {})
                if not isinstance(modifiers, dict):
                    raise ValueError("active_damage_done must be an object")
                if not all((result_name, grimoire, focus, source)):
                    raise ValueError(
                        "result_name, grimoire, focus, and source must be non-empty"
                    )
                semantics = RotationScribedSkillDamageSemantics(
                    result_name=result_name,
                    grimoire=grimoire,
                    focus=focus,
                    deals_direct_damage_on_activation=bool(
                        row["deals_direct_damage_on_activation"]
                    ),
                    persistent_toggle=bool(row["persistent_toggle"]),
                    active_damage_done=DamageDoneModifiers(
                        **{str(key): float(value) for key, value in modifiers.items()}
                    ),
                    source=source,
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"invalid scribed damage semantics registry entry {index}: {exc}"
                ) from exc

            canonical_identity = result_identity(semantics.result_name)
            expected_identity = (semantics.grimoire, semantics.focus)
            if canonical_identity != expected_identity:
                raise ValueError(
                    "scribed damage semantics identity does not match canonical scribing catalog: "
                    f"{semantics.result_name!r} -> {canonical_identity!r}, expected {expected_identity!r}"
                )
            if expected_identity in by_identity:
                raise ValueError(
                    "duplicate scribed damage semantics for "
                    f"{semantics.grimoire} + {semantics.focus}"
                )
            by_identity[expected_identity] = semantics
        return by_identity


__all__ = [
    "RotationScribedSkillDamageSemantics",
    "RotationScribedSkillDamageSemanticsService",
]
