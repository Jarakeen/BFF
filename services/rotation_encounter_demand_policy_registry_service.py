from __future__ import annotations

"""Read explicitly reviewed encounter-demand policy used by Rotation Generate."""

import json
from pathlib import Path

from engine.config import get_data_dir
from minmax.rotation_demand_window import RotationDemandKind, RotationDemandPattern
from services.encounter_rotation_demand_service import EncounterRotationDemandPolicy


DEFAULT_ROTATION_ENCOUNTER_DEMAND_POLICY = (
    get_data_dir() / "rotation_policy" / "encounter_demands.json"
)


class RotationEncounterDemandPolicyRegistryService:
    """Read-only reviewed policy for interpreting canonical encounter timeline facts.

    Registry presence is itself evidence. A missing encounter key means no reviewed
    policy has been persisted yet and returns ``None``. An encounter explicitly stored
    with an empty ``policies`` list returns ``()`` and means review concluded that this
    Generate scope has no encounter-demand policies.

    This service never derives policy from boss names, fact labels, encounter prose,
    role, class, or timeline payloads. Registry rows must name the exact canonical
    ``fact_key`` and all role interpretation fields explicitly.
    """

    def __init__(self, path: str | Path = DEFAULT_ROTATION_ENCOUNTER_DEMAND_POLICY) -> None:
        self.path = Path(path)
        self._policies = self._load(self.path)

    @classmethod
    def _load(
        cls,
        path: Path,
    ) -> dict[str, tuple[EncounterRotationDemandPolicy, ...]]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1:
            raise ValueError("rotation encounter demand policy requires schema_version 1")
        encounters = payload.get("encounters")
        if not isinstance(encounters, dict):
            raise ValueError("rotation encounter demand policy requires an encounters object")

        loaded: dict[str, tuple[EncounterRotationDemandPolicy, ...]] = {}
        for raw_encounter_id, raw_entry in encounters.items():
            encounter_id = str(raw_encounter_id or "").strip()
            if not encounter_id:
                raise ValueError("rotation encounter demand policy encounter_id cannot be empty")
            normalized_id = encounter_id.casefold()
            if normalized_id in loaded:
                raise ValueError(
                    f"duplicate rotation encounter demand policy encounter_id: {encounter_id}"
                )
            if not isinstance(raw_entry, dict):
                raise ValueError(
                    f"rotation encounter demand policy {encounter_id!r} must be an object"
                )
            raw_policies = raw_entry.get("policies")
            if not isinstance(raw_policies, list):
                raise ValueError(
                    f"rotation encounter demand policy {encounter_id!r} requires a policies list"
                )

            policies: list[EncounterRotationDemandPolicy] = []
            seen_fact_keys: set[str] = set()
            for raw_policy in raw_policies:
                if not isinstance(raw_policy, dict):
                    raise ValueError(
                        f"rotation encounter demand policy {encounter_id!r} entries must be objects"
                    )
                fact_key = str(raw_policy.get("fact_key") or "").strip()
                if not fact_key:
                    raise ValueError(
                        f"rotation encounter demand policy {encounter_id!r} requires fact_key"
                    )
                fact_identity = fact_key.casefold()
                if fact_identity in seen_fact_keys:
                    raise ValueError(
                        f"duplicate rotation encounter demand fact_key for {encounter_id!r}: "
                        f"{fact_key!r}"
                    )
                seen_fact_keys.add(fact_identity)

                unknown = set(raw_policy) - {
                    "fact_key",
                    "kind",
                    "pattern",
                    "lead_seconds",
                    "point_window_seconds",
                    "target_count",
                }
                if unknown:
                    raise ValueError(
                        f"rotation encounter demand policy {encounter_id!r} has unsupported "
                        f"fields for {fact_key!r}: {', '.join(sorted(unknown))}"
                    )

                policies.append(
                    EncounterRotationDemandPolicy(
                        fact_key=fact_key,
                        kind=RotationDemandKind(str(raw_policy.get("kind") or "")),
                        pattern=RotationDemandPattern(
                            str(raw_policy.get("pattern") or "")
                        ),
                        lead_seconds=float(raw_policy.get("lead_seconds", 0.0)),
                        point_window_seconds=(
                            None
                            if raw_policy.get("point_window_seconds") is None
                            else float(raw_policy["point_window_seconds"])
                        ),
                        target_count=int(raw_policy.get("target_count", 1)),
                    )
                )
            loaded[normalized_id] = tuple(policies)
        return loaded

    def policies_for(
        self,
        encounter_id: str,
    ) -> tuple[EncounterRotationDemandPolicy, ...] | None:
        key = str(encounter_id or "").strip().casefold()
        if not key:
            raise ValueError("rotation encounter demand policy lookup requires encounter_id")
        return self._policies.get(key)

    def configured_encounter_ids(self) -> tuple[str, ...]:
        return tuple(self._policies)


__all__ = [
    "DEFAULT_ROTATION_ENCOUNTER_DEMAND_POLICY",
    "RotationEncounterDemandPolicyRegistryService",
]
