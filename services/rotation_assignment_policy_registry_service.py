from __future__ import annotations

"""Read-only reviewed registry for executable rotation-assignment policy.

ProviderAssignment remains authoritative for ownership. This registry supplies only
reviewed rotation semantics keyed by exact encounter + requirement identity. It does
not infer strategy from role names, roster labels, requirement prose, or capability
presence.
"""

from dataclasses import dataclass
import json
from pathlib import Path

from engine.config import get_data_dir
from services.rotation_assignment_effect_obligation_service import (
    RotationAssignmentEffectPolicy,
)
from services.rotation_assignment_policy_resolver import RotationAssignmentNonEffectPolicy
from services.rotation_assignment_taunt_maintenance_service import (
    RotationAssignmentTauntMaintenancePolicy,
    RotationAssignmentTauntMaintenanceWindow,
)
from services.rotation_assignment_taunt_obligation_service import (
    RotationAssignmentTauntApplicationWindow,
    RotationAssignmentTauntPolicy,
)


DEFAULT_ROTATION_ASSIGNMENT_POLICY = (
    get_data_dir() / "rotation_assignment_policy" / "reviewed.json"
)


@dataclass(frozen=True)
class RotationAssignmentPolicyBundle:
    encounter_id: str
    effect_policies: tuple[RotationAssignmentEffectPolicy, ...] = ()
    taunt_policies: tuple[RotationAssignmentTauntPolicy, ...] = ()
    taunt_maintenance_policies: tuple[
        RotationAssignmentTauntMaintenancePolicy, ...
    ] = ()
    non_effect_policies: tuple[RotationAssignmentNonEffectPolicy, ...] = ()

    def __post_init__(self) -> None:
        encounter_id = str(self.encounter_id or "").strip()
        if not encounter_id:
            raise ValueError("rotation assignment policy bundle requires encounter_id")
        object.__setattr__(self, "encounter_id", encounter_id)
        for field_name in (
            "effect_policies",
            "taunt_policies",
            "taunt_maintenance_policies",
            "non_effect_policies",
        ):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))

    @property
    def empty(self) -> bool:
        return not any(
            (
                self.effect_policies,
                self.taunt_policies,
                self.taunt_maintenance_policies,
                self.non_effect_policies,
            )
        )


class RotationAssignmentPolicyRegistryService:
    """Load reviewed assignment policy without becoming mechanic or ownership truth."""

    def __init__(self, path: str | Path = DEFAULT_ROTATION_ASSIGNMENT_POLICY) -> None:
        self.path = Path(path)
        self._bundles = self._load(self.path)

    @classmethod
    def _load(cls, path: Path) -> dict[str, RotationAssignmentPolicyBundle]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("policies")
        if not isinstance(rows, list):
            raise ValueError("rotation assignment policy registry requires a policies list")

        by_encounter: dict[str, dict[str, list[object]]] = {}
        seen: set[tuple[str, str]] = set()
        for raw in rows:
            if not isinstance(raw, dict):
                raise ValueError("rotation assignment policy entries must be objects")
            kind = cls._required_text(raw, "kind").casefold()
            encounter_id = cls._required_text(raw, "encounter_id")
            requirement_id = cls._required_text(raw, "requirement_id")
            key = (encounter_id.casefold(), requirement_id.casefold())
            if key in seen:
                raise ValueError(
                    "rotation assignment policy registry cannot give one requirement multiple dispositions: "
                    f"{encounter_id!r} / {requirement_id!r}"
                )
            seen.add(key)

            groups = by_encounter.setdefault(
                encounter_id.casefold(),
                {
                    "encounter_id": [encounter_id],
                    "effect": [],
                    "taunt": [],
                    "taunt_maintenance": [],
                    "non_effect": [],
                },
            )
            if kind == "effect":
                groups["effect"].append(cls._effect(raw))
            elif kind == "taunt":
                groups["taunt"].append(cls._taunt(raw))
            elif kind == "taunt_maintenance":
                groups["taunt_maintenance"].append(cls._taunt_maintenance(raw))
            elif kind == "non_effect":
                groups["non_effect"].append(cls._non_effect(raw))
            else:
                raise ValueError(f"unsupported rotation assignment policy kind: {kind!r}")

        result: dict[str, RotationAssignmentPolicyBundle] = {}
        for encounter_key, groups in by_encounter.items():
            result[encounter_key] = RotationAssignmentPolicyBundle(
                encounter_id=str(groups["encounter_id"][0]),
                effect_policies=tuple(groups["effect"]),
                taunt_policies=tuple(groups["taunt"]),
                taunt_maintenance_policies=tuple(groups["taunt_maintenance"]),
                non_effect_policies=tuple(groups["non_effect"]),
            )
        return result

    @staticmethod
    def _required_text(raw: dict, key: str) -> str:
        value = str(raw.get(key) or "").strip()
        if not value:
            raise ValueError(f"rotation assignment policy {key} must be non-empty")
        return value

    @staticmethod
    def _optional_bar(raw: dict) -> str | None:
        value = raw.get("bar")
        return None if value is None else str(value)

    @staticmethod
    def _windows(raw: dict, *, kind: str) -> tuple[dict, ...]:
        windows = raw.get("windows")
        if not isinstance(windows, list):
            raise ValueError(f"rotation assignment {kind} policy windows must be a list")
        if any(not isinstance(window, dict) for window in windows):
            raise ValueError(
                f"rotation assignment {kind} policy windows must contain only objects"
            )
        return tuple(windows)

    @classmethod
    def _effect(cls, raw: dict) -> RotationAssignmentEffectPolicy:
        return RotationAssignmentEffectPolicy(
            requirement_id=cls._required_text(raw, "requirement_id"),
            encounter_id=cls._required_text(raw, "encounter_id"),
            requirement_type=cls._required_text(raw, "requirement_type"),
            effect_name=cls._required_text(raw, "effect_name"),
            source_skill_name=cls._required_text(raw, "source_skill_name"),
            minimum_uptime=float(raw.get("minimum_uptime")),
            source=cls._required_text(raw, "source"),
            bar=cls._optional_bar(raw),
        )

    @classmethod
    def _taunt(cls, raw: dict) -> RotationAssignmentTauntPolicy:
        windows = cls._windows(raw, kind="taunt")
        return RotationAssignmentTauntPolicy(
            requirement_id=cls._required_text(raw, "requirement_id"),
            encounter_id=cls._required_text(raw, "encounter_id"),
            requirement_type=cls._required_text(raw, "requirement_type"),
            source_skill_name=cls._required_text(raw, "source_skill_name"),
            source=cls._required_text(raw, "source"),
            windows=tuple(
                RotationAssignmentTauntApplicationWindow(
                    occurrence_id=cls._required_text(window, "occurrence_id"),
                    window_start_seconds=float(window.get("window_start_seconds")),
                    window_end_seconds=float(window.get("window_end_seconds")),
                    minimum_applications=int(window.get("minimum_applications", 1)),
                    bar=cls._optional_bar(window),
                    target_key=(
                        None
                        if window.get("target_key") is None
                        else str(window.get("target_key"))
                    ),
                )
                for window in windows
            ),
        )

    @classmethod
    def _taunt_maintenance(cls, raw: dict) -> RotationAssignmentTauntMaintenancePolicy:
        windows = cls._windows(raw, kind="taunt maintenance")
        return RotationAssignmentTauntMaintenancePolicy(
            requirement_id=cls._required_text(raw, "requirement_id"),
            encounter_id=cls._required_text(raw, "encounter_id"),
            requirement_type=cls._required_text(raw, "requirement_type"),
            source_skill_name=cls._required_text(raw, "source_skill_name"),
            source=cls._required_text(raw, "source"),
            windows=tuple(
                RotationAssignmentTauntMaintenanceWindow(
                    occurrence_id=cls._required_text(window, "occurrence_id"),
                    target_key=cls._required_text(window, "target_key"),
                    active_start_seconds=float(window.get("active_start_seconds")),
                    active_end_seconds=float(window.get("active_end_seconds")),
                    bar=cls._optional_bar(window),
                )
                for window in windows
            ),
        )

    @classmethod
    def _non_effect(cls, raw: dict) -> RotationAssignmentNonEffectPolicy:
        return RotationAssignmentNonEffectPolicy(
            requirement_id=cls._required_text(raw, "requirement_id"),
            encounter_id=cls._required_text(raw, "encounter_id"),
            requirement_type=cls._required_text(raw, "requirement_type"),
            reason=cls._required_text(raw, "reason"),
            source=cls._required_text(raw, "source"),
        )

    def for_encounter(self, encounter_id: str) -> RotationAssignmentPolicyBundle:
        resolved = str(encounter_id or "").strip()
        if not resolved:
            raise ValueError("rotation assignment policy lookup requires encounter_id")
        return self._bundles.get(
            resolved.casefold(),
            RotationAssignmentPolicyBundle(encounter_id=resolved),
        )


__all__ = [
    "DEFAULT_ROTATION_ASSIGNMENT_POLICY",
    "RotationAssignmentPolicyBundle",
    "RotationAssignmentPolicyRegistryService",
]
