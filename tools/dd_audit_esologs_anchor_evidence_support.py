from __future__ import annotations

"""Load reviewed ESO Logs cast/impact observations for DD audit replay.

This audit-only bridge turns an explicit, versioned JSON observation file into the
existing canonical runtime activation-anchor evidence. It preserves report/fight/
source/event provenance and delegates exact action matching to
``RotationDDPeriodicEsoLogsReplayAnchorMappingService``.

The bridge deliberately does not infer impact timestamps from aggregate delay
statistics. Unlinked observations, stale action times, conflicting observations, and
other mapper gaps remain unresolved and therefore fail closed. For every skill
identity present in the reviewed file, audit mapping is additionally all-or-nothing:
all final-plan occurrences of that skill must receive exact mapped evidence or none of
that skill's partial evidence is returned.
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path

from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.skill_coefficient_repository import ability_entity_id
from services.rotation_dd_periodic_esologs_anchor_correlation_service import (
    RotationDDPeriodicEsoLogsCastImpactObservation,
)
from services.rotation_dd_periodic_esologs_replay_anchor_mapping_service import (
    RotationDDPeriodicEsoLogsReplayAnchorMappingResult,
    RotationDDPeriodicEsoLogsReplayAnchorMappingService,
)


@dataclass(frozen=True)
class DDAuditEsoLogsAnchorEvidenceFile:
    replay_origin_timestamp_ms: float
    observations: tuple[RotationDDPeriodicEsoLogsCastImpactObservation, ...]
    source: str


class DDAuditEsoLogsAnchorEvidenceSupport:
    """Parse exact reviewed observations and map them onto one final audit plan."""

    SCHEMA_VERSION = 1

    def __init__(
        self,
        *,
        mapping_service: RotationDDPeriodicEsoLogsReplayAnchorMappingService | None = None,
    ) -> None:
        self.mapping_service = (
            mapping_service or RotationDDPeriodicEsoLogsReplayAnchorMappingService()
        )

    def load(self, path: str | Path) -> DDAuditEsoLogsAnchorEvidenceFile:
        source_path = Path(path)
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("ESO Logs anchor evidence file must be a JSON object")
        if payload.get("schema_version") != self.SCHEMA_VERSION:
            raise ValueError("ESO Logs anchor evidence schema_version must be 1")

        origin = self._finite_non_negative(
            payload.get("replay_origin_timestamp_ms"),
            label="replay_origin_timestamp_ms",
        )
        rows = payload.get("observations")
        if not isinstance(rows, list) or not rows:
            raise ValueError("ESO Logs anchor evidence observations must be a non-empty list")

        observations = tuple(
            self._observation(row, index=index)
            for index, row in enumerate(rows)
        )
        return DDAuditEsoLogsAnchorEvidenceFile(
            replay_origin_timestamp_ms=origin,
            observations=observations,
            source=str(source_path),
        )

    def map_file(
        self,
        path: str | Path,
        *,
        plan: RotationPlan,
    ) -> RotationDDPeriodicEsoLogsReplayAnchorMappingResult:
        loaded = self.load(path)
        mapped = self.mapping_service.map(
            plan=plan,
            observations=loaded.observations,
            replay_origin_timestamp_ms=loaded.replay_origin_timestamp_ms,
        )
        return self._require_complete_observed_skill_coverage(
            plan=plan,
            observations=loaded.observations,
            mapped=mapped,
        )

    def _require_complete_observed_skill_coverage(
        self,
        *,
        plan: RotationPlan,
        observations: tuple[RotationDDPeriodicEsoLogsCastImpactObservation, ...],
        mapped: RotationDDPeriodicEsoLogsReplayAnchorMappingResult,
    ) -> RotationDDPeriodicEsoLogsReplayAnchorMappingResult:
        identities = tuple(
            dict.fromkeys(
                identity
                for item in observations
                if (identity := ability_entity_id(item.skill_entity_id))
            )
        )
        evidence = list(mapped.evidence)
        unresolved = list(mapped.unresolved)

        for identity in identities:
            plan_count = sum(
                1
                for action in plan.actions
                if action.kind is RotationActionKind.SKILL
                and ability_entity_id(action.name or "") == identity
            )
            evidence_count = sum(
                1 for row in evidence if row.skill_entity_id == identity
            )
            if evidence_count == plan_count and plan_count > 0:
                continue

            evidence = [row for row in evidence if row.skill_entity_id != identity]
            unresolved.append(
                f"{identity}: reviewed ESO Logs impact evidence covers "
                f"{evidence_count} of {plan_count} final-plan occurrence(s); "
                "partial audit anchor coverage is not executable"
            )

        return RotationDDPeriodicEsoLogsReplayAnchorMappingResult(
            evidence=tuple(evidence),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def _observation(
        self,
        raw: object,
        *,
        index: int,
    ) -> RotationDDPeriodicEsoLogsCastImpactObservation:
        if not isinstance(raw, dict):
            raise ValueError(f"ESO Logs anchor observation {index} must be an object")

        def required_text(name: str) -> str:
            value = str(raw.get(name) or "").strip()
            if not value:
                raise ValueError(
                    f"ESO Logs anchor observation {index} requires non-empty {name}"
                )
            return value

        def required_int(name: str, *, positive: bool = False) -> int:
            value = raw.get(name)
            if isinstance(value, bool):
                raise ValueError(
                    f"ESO Logs anchor observation {index} {name} must be an integer"
                )
            try:
                resolved = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"ESO Logs anchor observation {index} {name} must be an integer"
                ) from exc
            if positive and resolved <= 0:
                raise ValueError(
                    f"ESO Logs anchor observation {index} {name} must be positive"
                )
            if not positive and resolved < 0:
                raise ValueError(
                    f"ESO Logs anchor observation {index} {name} must be non-negative"
                )
            return resolved

        cast_ability_raw = raw.get("cast_ability_id")
        cast_ability_id = (
            None
            if cast_ability_raw is None
            else required_int("cast_ability_id", positive=True)
        )
        track_raw = raw.get("cast_track_id")
        cast_track_id = (
            None
            if track_raw is None
            else required_int("cast_track_id", positive=True)
        )
        linked = raw.get("cast_track_linked")
        if not isinstance(linked, bool):
            raise ValueError(
                f"ESO Logs anchor observation {index} cast_track_linked must be boolean"
            )

        return RotationDDPeriodicEsoLogsCastImpactObservation(
            skill_entity_id=required_text("skill_entity_id"),
            report_code=required_text("report_code"),
            fight_id=required_int("fight_id", positive=True),
            source_id=required_int("source_id", positive=True),
            cast_event_index=required_int("cast_event_index"),
            cast_timestamp_ms=self._finite_non_negative(
                raw.get("cast_timestamp_ms"),
                label=f"observation {index} cast_timestamp_ms",
            ),
            cast_ability_id=cast_ability_id,
            impact_event_index=required_int("impact_event_index"),
            impact_timestamp_ms=self._finite_non_negative(
                raw.get("impact_timestamp_ms"),
                label=f"observation {index} impact_timestamp_ms",
            ),
            impact_ability_id=required_int("impact_ability_id", positive=True),
            cast_track_id=cast_track_id,
            cast_track_linked=linked,
        )

    @staticmethod
    def _finite_non_negative(raw: object, *, label: str) -> float:
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} must be numeric") from exc
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f"{label} must be finite and non-negative")
        return value


__all__ = [
    "DDAuditEsoLogsAnchorEvidenceFile",
    "DDAuditEsoLogsAnchorEvidenceSupport",
]
