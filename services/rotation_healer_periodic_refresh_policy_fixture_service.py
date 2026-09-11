from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path

from services.rotation_healer_periodic_runtime_evidence_service import (
    RotationHealerPeriodicRefreshPolicy,
    RotationHealerReviewedRuntimeObservation,
)


@dataclass(frozen=True)
class RotationHealerReviewedRefreshPolicy:
    source_name: str
    coefficient_number: int
    game_version: str
    refresh_policy: RotationHealerPeriodicRefreshPolicy
    provenance: tuple[str, ...]


@dataclass(frozen=True)
class RotationHealerRefreshPolicyFixtureReport:
    source_path: str
    schema_version: int
    policies: tuple[RotationHealerReviewedRefreshPolicy, ...]
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class RotationHealerRefreshPolicyComposition:
    observations: tuple[RotationHealerReviewedRuntimeObservation, ...]
    unresolved: tuple[str, ...] = ()


class RotationHealerPeriodicRefreshPolicyFixtureService:
    """Load explicitly reviewed periodic refresh policies and compose them into timing evidence.

    Refresh/recast evidence remains separate from isolated single-application timing evidence.
    This service never infers a policy from logs. It only loads a reviewed fixture and applies
    an exact identity/version match to already-reviewed runtime observations.
    """

    SCHEMA_VERSION = 1

    def load(self, path: str | Path) -> RotationHealerRefreshPolicyFixtureReport:
        source_path = Path(path)
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("healer refresh policy fixture root must be an object")

        schema_version = int(payload.get("schema_version", 0))
        if schema_version != self.SCHEMA_VERSION:
            raise ValueError(f"unsupported healer refresh policy schema_version: {schema_version}")
        review_status = str(payload.get("review_status") or "").strip().casefold()
        if review_status != "reviewed":
            raise ValueError(
                "healer refresh policy fixture is not reviewed; "
                f"review_status={review_status!r}"
            )

        default_game_version = str(payload.get("game_version") or "").strip()
        raw_policies = payload.get("policies")
        if not isinstance(raw_policies, list):
            raise ValueError("healer refresh policy fixture policies must be a list")

        policies: list[RotationHealerReviewedRefreshPolicy] = []
        unresolved: list[str] = []
        seen: set[tuple[str, int, str]] = set()
        for index, raw in enumerate(raw_policies, start=1):
            if not isinstance(raw, dict):
                unresolved.append(f"policy {index}: entry must be an object")
                continue
            try:
                source_name = str(raw["source_name"]).strip()
                coefficient_number = int(raw["coefficient_number"])
                game_version = str(raw.get("game_version") or default_game_version).strip()
                policy = RotationHealerPeriodicRefreshPolicy(str(raw["refresh_policy"]).strip().casefold())
                provenance_raw = raw.get("provenance")
                if isinstance(provenance_raw, str):
                    provenance_raw = [provenance_raw]
                if not source_name or coefficient_number <= 0 or not game_version:
                    raise ValueError("source_name, positive coefficient_number, and game_version are required")
                if not isinstance(provenance_raw, list) or not provenance_raw:
                    raise ValueError("non-empty provenance is required")
                provenance = tuple(str(value).strip() for value in provenance_raw if str(value).strip())
                if not provenance:
                    raise ValueError("non-empty provenance is required")
            except (KeyError, TypeError, ValueError) as exc:
                unresolved.append(f"policy {index}: {exc}")
                continue

            key = (source_name.casefold(), coefficient_number, game_version)
            if key in seen:
                unresolved.append(
                    f"policy {index}: duplicate refresh policy identity {source_name} "
                    f"coefficient {coefficient_number} [{game_version}]"
                )
                continue
            seen.add(key)
            policies.append(
                RotationHealerReviewedRefreshPolicy(
                    source_name=source_name,
                    coefficient_number=coefficient_number,
                    game_version=game_version,
                    refresh_policy=policy,
                    provenance=provenance,
                )
            )

        return RotationHealerRefreshPolicyFixtureReport(
            source_path=str(source_path),
            schema_version=schema_version,
            policies=tuple(policies),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def compose(
        observations: tuple[RotationHealerReviewedRuntimeObservation, ...],
        fixture: RotationHealerRefreshPolicyFixtureReport,
    ) -> RotationHealerRefreshPolicyComposition:
        policy_map = {
            (item.source_name.casefold(), int(item.coefficient_number), item.game_version): item
            for item in fixture.policies
        }
        used: set[tuple[str, int, str]] = set()
        unresolved: list[str] = list(fixture.unresolved)
        composed: list[RotationHealerReviewedRuntimeObservation] = []

        for observation in observations:
            version = str(observation.game_version or "")
            key = (observation.source_name.casefold(), int(observation.coefficient_number), version)
            reviewed = policy_map.get(key)
            if reviewed is None:
                composed.append(observation)
                continue
            used.add(key)
            if observation.refresh_policy is not None and observation.refresh_policy is not reviewed.refresh_policy:
                unresolved.append(
                    f"{observation.source_name} coefficient {observation.coefficient_number}: "
                    "reviewed refresh policy conflicts with existing runtime observation"
                )
                composed.append(observation)
                continue
            composed.append(
                replace(
                    observation,
                    refresh_policy=reviewed.refresh_policy,
                    provenance=tuple(
                        dict.fromkeys(
                            tuple(observation.provenance)
                            + tuple(reviewed.provenance)
                            + (
                                f"reviewed refresh/recast policy: {reviewed.refresh_policy.value}",
                            )
                        )
                    ),
                )
            )

        for key, reviewed in policy_map.items():
            if key not in used:
                unresolved.append(
                    f"{reviewed.source_name} coefficient {reviewed.coefficient_number} "
                    f"[{reviewed.game_version}]: no matching reviewed runtime timing observation"
                )

        return RotationHealerRefreshPolicyComposition(
            observations=tuple(composed),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "RotationHealerPeriodicRefreshPolicyFixtureService",
    "RotationHealerRefreshPolicyFixtureReport",
    "RotationHealerRefreshPolicyComposition",
    "RotationHealerReviewedRefreshPolicy",
]
