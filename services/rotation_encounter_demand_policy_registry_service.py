from __future__ import annotations

"""Read explicitly reviewed encounter-demand policy used by Rotation Generate."""

from dataclasses import dataclass
import json
from pathlib import Path

from engine.config import get_data_dir
from minmax.rotation_demand_window import RotationDemandKind, RotationDemandPattern
from services.encounter_rotation_demand_service import EncounterRotationDemandPolicy
from services.encounter_threshold_rotation_demand_service import (
    EncounterThresholdRotationDemandPolicy,
)


DEFAULT_ROTATION_ENCOUNTER_DEMAND_POLICY = (
    get_data_dir() / "rotation_policy" / "encounter_demands.json"
)


@dataclass(frozen=True)
class RotationEncounterDemandPolicyReviewBlocker:
    """Persisted review debt for a partly researched encounter-demand policy.

    Review blockers preserve what still needs an explicit decision without promoting
    audit defaults or encounter prose into executable rotation policy.
    """

    key: str
    summary: str
    needed_evidence: str
    source_context: str = ""


@dataclass(frozen=True)
class RotationEncounterDemandPolicyRegistryEntry:
    """Reviewed role interpretation for one canonical encounter.

    Clock policies consume reviewed timeline facts that already carry explicit seconds.
    Threshold policies consume reviewed boss-health threshold facts and therefore still
    require an explicit raid-damage trajectory before they can become clock windows.

    Review blockers are non-executable policy research debt. Their presence means the
    encounter has been reviewed enough to identify a specific missing decision, but not
    enough to safely emit canonical rotation demands yet.
    """

    clock_policies: tuple[EncounterRotationDemandPolicy, ...] = ()
    threshold_policies: tuple[EncounterThresholdRotationDemandPolicy, ...] = ()
    review_blockers: tuple[RotationEncounterDemandPolicyReviewBlocker, ...] = ()


class RotationEncounterDemandPolicyRegistryService:
    """Read-only reviewed policy for interpreting canonical encounter facts.

    Registry presence is itself evidence. A missing encounter key means no reviewed
    policy has been persisted yet and returns ``None``. An encounter explicitly stored
    with empty policy lists and no review blockers means review concluded that this
    Generate scope has no encounter-demand policies.

    Clock-timed and health-threshold policies remain separate evidence families. This
    service never converts health thresholds to seconds, invents raid DPS, or derives
    policy from boss names, fact labels, encounter prose, role, or class. Partly reviewed
    encounters may persist structured review blockers so Generate can fail closed with a
    precise reason instead of pretending no research exists.
    """

    def __init__(self, path: str | Path = DEFAULT_ROTATION_ENCOUNTER_DEMAND_POLICY) -> None:
        self.path = Path(path)
        self._entries = self._load(self.path)

    @classmethod
    def _load(
        cls,
        path: Path,
    ) -> dict[str, RotationEncounterDemandPolicyRegistryEntry]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 2:
            raise ValueError("rotation encounter demand policy requires schema_version 2")
        encounters = payload.get("encounters")
        if not isinstance(encounters, dict):
            raise ValueError("rotation encounter demand policy requires an encounters object")

        loaded: dict[str, RotationEncounterDemandPolicyRegistryEntry] = {}
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
            unknown_entry = set(raw_entry) - {
                "clock_policies",
                "threshold_policies",
                "review_blockers",
            }
            if unknown_entry:
                raise ValueError(
                    f"rotation encounter demand policy {encounter_id!r} has unsupported "
                    f"entry fields: {', '.join(sorted(unknown_entry))}"
                )

            raw_clock = raw_entry.get("clock_policies", [])
            raw_threshold = raw_entry.get("threshold_policies", [])
            raw_blockers = raw_entry.get("review_blockers", [])
            if not isinstance(raw_clock, list):
                raise ValueError(
                    f"rotation encounter demand policy {encounter_id!r} requires a clock_policies list"
                )
            if not isinstance(raw_threshold, list):
                raise ValueError(
                    f"rotation encounter demand policy {encounter_id!r} requires a threshold_policies list"
                )
            if not isinstance(raw_blockers, list):
                raise ValueError(
                    f"rotation encounter demand policy {encounter_id!r} requires a review_blockers list"
                )

            loaded[normalized_id] = RotationEncounterDemandPolicyRegistryEntry(
                clock_policies=cls._clock_policies(encounter_id, raw_clock),
                threshold_policies=cls._threshold_policies(encounter_id, raw_threshold),
                review_blockers=cls._review_blockers(encounter_id, raw_blockers),
            )
        return loaded

    @staticmethod
    def _clock_policies(
        encounter_id: str,
        rows: list[object],
    ) -> tuple[EncounterRotationDemandPolicy, ...]:
        policies: list[EncounterRotationDemandPolicy] = []
        seen_fact_keys: set[str] = set()
        for raw_policy in rows:
            if not isinstance(raw_policy, dict):
                raise ValueError(
                    f"rotation encounter clock policy {encounter_id!r} entries must be objects"
                )
            fact_key = str(raw_policy.get("fact_key") or "").strip()
            if not fact_key:
                raise ValueError(
                    f"rotation encounter clock policy {encounter_id!r} requires fact_key"
                )
            identity = fact_key.casefold()
            if identity in seen_fact_keys:
                raise ValueError(
                    f"duplicate rotation encounter clock fact_key for {encounter_id!r}: {fact_key!r}"
                )
            seen_fact_keys.add(identity)
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
                    f"rotation encounter clock policy {encounter_id!r} has unsupported "
                    f"fields for {fact_key!r}: {', '.join(sorted(unknown))}"
                )
            policies.append(
                EncounterRotationDemandPolicy(
                    fact_key=fact_key,
                    kind=RotationDemandKind(str(raw_policy.get("kind") or "")),
                    pattern=RotationDemandPattern(str(raw_policy.get("pattern") or "")),
                    lead_seconds=float(raw_policy.get("lead_seconds", 0.0)),
                    point_window_seconds=(
                        None
                        if raw_policy.get("point_window_seconds") is None
                        else float(raw_policy["point_window_seconds"])
                    ),
                    target_count=int(raw_policy.get("target_count", 1)),
                )
            )
        return tuple(policies)

    @staticmethod
    def _threshold_policies(
        encounter_id: str,
        rows: list[object],
    ) -> tuple[EncounterThresholdRotationDemandPolicy, ...]:
        policies: list[EncounterThresholdRotationDemandPolicy] = []
        seen: set[tuple[str, float]] = set()
        for raw_policy in rows:
            if not isinstance(raw_policy, dict):
                raise ValueError(
                    f"rotation encounter threshold policy {encounter_id!r} entries must be objects"
                )
            fact_key = str(raw_policy.get("fact_key") or "").strip()
            if not fact_key:
                raise ValueError(
                    f"rotation encounter threshold policy {encounter_id!r} requires fact_key"
                )
            if "threshold_fraction" not in raw_policy:
                raise ValueError(
                    f"rotation encounter threshold policy {encounter_id!r} requires threshold_fraction"
                )
            threshold_fraction = float(raw_policy["threshold_fraction"])
            identity = (fact_key.casefold(), threshold_fraction)
            if identity in seen:
                raise ValueError(
                    "duplicate rotation encounter threshold policy for "
                    f"{encounter_id!r}: {fact_key!r} at {threshold_fraction * 100:g}%"
                )
            seen.add(identity)
            unknown = set(raw_policy) - {
                "fact_key",
                "threshold_fraction",
                "kind",
                "pattern",
                "lead_seconds",
                "window_seconds",
                "target_count",
                "name",
            }
            if unknown:
                raise ValueError(
                    f"rotation encounter threshold policy {encounter_id!r} has unsupported "
                    f"fields for {fact_key!r}: {', '.join(sorted(unknown))}"
                )
            policies.append(
                EncounterThresholdRotationDemandPolicy(
                    fact_key=fact_key,
                    threshold_fraction=threshold_fraction,
                    kind=RotationDemandKind(str(raw_policy.get("kind") or "")),
                    pattern=RotationDemandPattern(str(raw_policy.get("pattern") or "")),
                    lead_seconds=float(raw_policy.get("lead_seconds", 0.0)),
                    window_seconds=float(raw_policy.get("window_seconds", 1.0)),
                    target_count=int(raw_policy.get("target_count", 1)),
                    name=str(raw_policy.get("name") or ""),
                )
            )
        return tuple(policies)

    @staticmethod
    def _review_blockers(
        encounter_id: str,
        rows: list[object],
    ) -> tuple[RotationEncounterDemandPolicyReviewBlocker, ...]:
        blockers: list[RotationEncounterDemandPolicyReviewBlocker] = []
        seen_keys: set[str] = set()
        for raw_blocker in rows:
            if not isinstance(raw_blocker, dict):
                raise ValueError(
                    f"rotation encounter demand review blockers {encounter_id!r} must be objects"
                )
            unknown = set(raw_blocker) - {
                "key",
                "summary",
                "needed_evidence",
                "source_context",
            }
            if unknown:
                raise ValueError(
                    f"rotation encounter demand review blocker {encounter_id!r} has unsupported "
                    f"fields: {', '.join(sorted(unknown))}"
                )
            key = str(raw_blocker.get("key") or "").strip()
            summary = str(raw_blocker.get("summary") or "").strip()
            needed_evidence = str(raw_blocker.get("needed_evidence") or "").strip()
            source_context = str(raw_blocker.get("source_context") or "").strip()
            if not key or not summary or not needed_evidence:
                raise ValueError(
                    f"rotation encounter demand review blocker {encounter_id!r} requires "
                    "key, summary, and needed_evidence"
                )
            identity = key.casefold()
            if identity in seen_keys:
                raise ValueError(
                    f"duplicate rotation encounter demand review blocker for {encounter_id!r}: {key!r}"
                )
            seen_keys.add(identity)
            blockers.append(
                RotationEncounterDemandPolicyReviewBlocker(
                    key=key,
                    summary=summary,
                    needed_evidence=needed_evidence,
                    source_context=source_context,
                )
            )
        return tuple(blockers)

    def entry_for(
        self,
        encounter_id: str,
    ) -> RotationEncounterDemandPolicyRegistryEntry | None:
        key = str(encounter_id or "").strip().casefold()
        if not key:
            raise ValueError("rotation encounter demand policy lookup requires encounter_id")
        return self._entries.get(key)

    def policies_for(
        self,
        encounter_id: str,
    ) -> tuple[EncounterRotationDemandPolicy, ...] | None:
        entry = self.entry_for(encounter_id)
        return None if entry is None else entry.clock_policies

    def threshold_policies_for(
        self,
        encounter_id: str,
    ) -> tuple[EncounterThresholdRotationDemandPolicy, ...] | None:
        entry = self.entry_for(encounter_id)
        return None if entry is None else entry.threshold_policies

    def review_blockers_for(
        self,
        encounter_id: str,
    ) -> tuple[RotationEncounterDemandPolicyReviewBlocker, ...] | None:
        entry = self.entry_for(encounter_id)
        return None if entry is None else entry.review_blockers

    def configured_encounter_ids(self) -> tuple[str, ...]:
        return tuple(self._entries)


__all__ = [
    "DEFAULT_ROTATION_ENCOUNTER_DEMAND_POLICY",
    "RotationEncounterDemandPolicyRegistryEntry",
    "RotationEncounterDemandPolicyReviewBlocker",
    "RotationEncounterDemandPolicyRegistryService",
]
