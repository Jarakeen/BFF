from __future__ import annotations

"""Deterministic read-only access to canonical encounter source records."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from services.encounter_projection import EncounterDefinition, load_encounter_definition


class EncounterSourceError(ValueError):
    """The canonical source corpus is malformed or internally ambiguous."""


class EncounterNotFoundError(LookupError):
    """No canonical boss source exists for the exact requested encounter id."""


@dataclass(frozen=True)
class EncounterRepository:
    boss_root: Path
    evidence_root: Path
    _boss_paths: dict[str, Path] = field(init=False, repr=False, compare=False)
    _evidence_paths: dict[str, Path] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_boss_paths", self._index(self.boss_root, "id"))
        object.__setattr__(self, "_evidence_paths", self._index(self.evidence_root, "encounter_id"))

    @staticmethod
    def _index(root: Path, identity_key: str) -> dict[str, Path]:
        if not root.is_dir():
            raise EncounterSourceError(f"Canonical encounter directory is missing: {root}")
        indexed: dict[str, Path] = {}
        for path in sorted(root.glob("*.json"), key=lambda item: item.name.casefold()):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise EncounterSourceError(f"Invalid canonical encounter JSON: {path}") from exc
            identity = payload.get(identity_key) if isinstance(payload, dict) else None
            if not isinstance(identity, str) or not identity.strip():
                raise EncounterSourceError(f"Missing {identity_key!r} in canonical encounter JSON: {path}")
            if identity in indexed:
                raise EncounterSourceError(
                    f"Duplicate canonical encounter {identity_key} {identity!r}: {indexed[identity]} and {path}"
                )
            indexed[identity] = path
        return indexed

    @classmethod
    def from_data_root(cls, data_root: Path) -> "EncounterRepository":
        return cls(data_root / "eso_info" / "bosses", data_root / "encounter_evidence")

    def encounter_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._boss_paths))

    def get(self, encounter_id: str) -> EncounterDefinition:
        if not isinstance(encounter_id, str) or not encounter_id:
            raise ValueError("encounter_id must be a non-empty canonical id")
        boss_path = self._boss_paths.get(encounter_id)
        if boss_path is None:
            raise EncounterNotFoundError(f"No canonical encounter source for id {encounter_id!r}")
        return load_encounter_definition(boss_path, evidence_packet_path=self._evidence_paths.get(encounter_id))
