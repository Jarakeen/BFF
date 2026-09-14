from __future__ import annotations

"""Read reviewed target/source-scoped taunt-state lifecycle identity.

This service owns the reviewed mapping between the combat-log debuff state and canonical
Taunt semantics. It does not infer encounter obligations or invent missing duration.
Observed intervals must come from explicit apply/remove lifecycle evidence.
"""

from dataclasses import dataclass
import json
from pathlib import Path


_DEFAULT_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "encounter_taunt_state"
    / "reviewed.json"
)


@dataclass(frozen=True)
class ReviewedTauntStateLifecycle:
    state_id: str
    ability_id: int
    effect_name: str
    scope: str
    reviewed: bool
    evidence: tuple[str, ...]
    interpretation: str

    def __post_init__(self) -> None:
        state_id = str(self.state_id or "").strip()
        effect_name = str(self.effect_name or "").strip()
        scope = str(self.scope or "").strip()
        interpretation = str(self.interpretation or "").strip()
        if not all((state_id, effect_name, scope, interpretation)):
            raise ValueError("reviewed taunt-state lifecycle fields must be non-empty")
        if int(self.ability_id) <= 0:
            raise ValueError("reviewed taunt-state ability_id must be positive")
        if not self.reviewed:
            raise ValueError("reviewed taunt-state lifecycle row must be reviewed")
        if scope != "source_target_debuff_state":
            raise ValueError(f"unsupported reviewed taunt-state scope: {scope!r}")
        evidence = tuple(dict.fromkeys(str(item or "").strip() for item in self.evidence))
        if not evidence or any(not item for item in evidence):
            raise ValueError("reviewed taunt-state lifecycle requires evidence")
        object.__setattr__(self, "state_id", state_id)
        object.__setattr__(self, "effect_name", effect_name)
        object.__setattr__(self, "scope", scope)
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "interpretation", interpretation)


class RotationTankTauntStateLifecycleService:
    def __init__(self, path: str | Path = _DEFAULT_PATH) -> None:
        self.path = Path(path)
        self._states = self._load(self.path)

    @staticmethod
    def _load(path: Path) -> dict[str, ReviewedTauntStateLifecycle]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if int(payload.get("schema_version", 0)) != 1:
            raise ValueError("unsupported reviewed taunt-state schema_version")
        rows = payload.get("states")
        if not isinstance(rows, list):
            raise ValueError("reviewed taunt-state states must be a list")
        result: dict[str, ReviewedTauntStateLifecycle] = {}
        for raw in rows:
            if not isinstance(raw, dict):
                raise ValueError("reviewed taunt-state rows must be objects")
            row = ReviewedTauntStateLifecycle(
                state_id=str(raw.get("state_id") or ""),
                ability_id=int(raw.get("ability_id") or 0),
                effect_name=str(raw.get("effect_name") or ""),
                scope=str(raw.get("scope") or ""),
                reviewed=bool(raw.get("reviewed")),
                evidence=tuple(raw.get("evidence") or ()),
                interpretation=str(raw.get("interpretation") or ""),
            )
            key = row.state_id.casefold()
            if key in result:
                raise ValueError(f"duplicate reviewed taunt-state id: {row.state_id!r}")
            result[key] = row
        return result

    def reviewed_for(self, state_id: str = "taunt") -> ReviewedTauntStateLifecycle | None:
        key = str(state_id or "").strip().casefold()
        if not key:
            raise ValueError("reviewed taunt-state lookup requires state_id")
        return self._states.get(key)


__all__ = [
    "ReviewedTauntStateLifecycle",
    "RotationTankTauntStateLifecycleService",
]
