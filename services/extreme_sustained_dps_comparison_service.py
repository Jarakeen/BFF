from __future__ import annotations

"""Compare explicit saved-build sustained-DPS witnesses.

This service belongs to the Optimization/Extreme layer. It consumes the
simulation-backed single-build evaluator and may compare supplied candidates,
but it never changes Combat Simulation mechanics or manufactures missing
candidate evidence.
"""

from dataclasses import dataclass
from pathlib import Path

from models.build_model import PlayerBuild
from services.extreme_saved_rotation_combat_record_service import (
    ExtremeSavedRotationCombatRecordService,
    ExtremeSavedRotationSustainedDPSResult,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSComparisonCandidate:
    build: PlayerBuild
    label: str
    modeled_dps: float | None
    duration_seconds: float | None
    mechanic_complete: bool
    result: ExtremeSavedRotationSustainedDPSResult


@dataclass(frozen=True)
class ExtremeSustainedDPSComparisonResult:
    ranked_candidates: tuple[ExtremeSustainedDPSComparisonCandidate, ...]
    leader: ExtremeSustainedDPSComparisonCandidate | None
    comparison_complete: bool
    target_health: int
    target_resistance: float
    target_name: str
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def candidate_count(self) -> int:
        return len(self.ranked_candidates)


class ExtremeSustainedDPSComparisonService:
    """Compare only explicitly supplied saved DD build/rotation witnesses."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        evaluator: ExtremeSavedRotationCombatRecordService | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.evaluator = evaluator or ExtremeSavedRotationCombatRecordService(
            self.database_path
        )

    @staticmethod
    def _label(build: PlayerBuild, index: int) -> str:
        build_name = str(getattr(build, "BuildName", "") or "").strip()
        character = str(getattr(build, "Name", "") or "").strip()
        build_id = str(getattr(build, "BuildId", "") or "").strip()
        if character and build_name:
            return f"{character} — {build_name}"
        if build_name:
            return build_name
        if build_id:
            return build_id
        if character:
            return character
        return f"Candidate {index + 1}"

    @staticmethod
    def _dedupe(values) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                str(value).strip()
                for value in values
                if str(value).strip()
            )
        )

    def compare(
        self,
        builds: tuple[PlayerBuild, ...],
        *,
        target_health: int,
        target_resistance: float,
        target_name: str = "Boss",
    ) -> ExtremeSustainedDPSComparisonResult:
        candidates = tuple(builds)
        if len(candidates) < 2:
            raise ValueError("sustained DPS comparison requires at least two candidates")
        if int(target_health) <= 0:
            raise ValueError("sustained DPS comparison target_health must be positive")
        if float(target_resistance) < 0:
            raise ValueError(
                "sustained DPS comparison target_resistance cannot be negative"
            )
        target = str(target_name or "").strip() or "Boss"

        rows: list[ExtremeSustainedDPSComparisonCandidate] = []
        unresolved: list[str] = []
        for index, build in enumerate(candidates):
            result = self.evaluator.sustained_dps(
                build,
                target_health=int(target_health),
                target_resistance=float(target_resistance),
                target_name=target,
            )
            record = result.record
            label = self._label(build, index)
            rows.append(
                ExtremeSustainedDPSComparisonCandidate(
                    build=build,
                    label=label,
                    modeled_dps=(
                        None if record is None else float(record.modeled_dps)
                    ),
                    duration_seconds=(
                        None if record is None else float(record.duration_seconds)
                    ),
                    mechanic_complete=bool(result.mechanic_complete),
                    result=result,
                )
            )
            for message in result.unresolved:
                unresolved.append(f"{label}: {message}")

        ranked = tuple(
            sorted(
                rows,
                key=lambda row: (
                    row.modeled_dps is None,
                    -(row.modeled_dps or 0.0),
                    row.label.casefold(),
                ),
            )
        )

        all_modeled = all(row.modeled_dps is not None for row in ranked)
        all_complete = all(row.mechanic_complete for row in ranked)
        horizons = {
            row.duration_seconds
            for row in ranked
            if row.duration_seconds is not None
        }
        shared_horizon = len(horizons) == 1 and len(horizons) > 0
        if all_modeled and not shared_horizon:
            unresolved.append(
                "Candidate execution horizons differ; sustained-DPS winner is withheld"
            )

        unique_top = False
        if all_modeled and ranked:
            top = ranked[0].modeled_dps
            assert top is not None
            tied = tuple(
                row
                for row in ranked
                if row.modeled_dps is not None
                and abs(float(row.modeled_dps) - float(top)) <= 1e-9
            )
            unique_top = len(tied) == 1
            if len(tied) > 1:
                unresolved.append(
                    "Top sustained-DPS candidates are tied; unique leader is unavailable"
                )

        comparison_complete = (
            all_modeled
            and all_complete
            and shared_horizon
            and unique_top
        )
        leader = ranked[0] if comparison_complete else None

        evidence = (
            f"Compared {len(ranked)} explicitly supplied saved-build candidates",
            f"Explicit target Health: {int(target_health)}",
            f"Explicit target resistance: {float(target_resistance):g}",
            "Every candidate evaluated through the same simulation-backed sustained-DPS evaluator",
        )
        return ExtremeSustainedDPSComparisonResult(
            ranked_candidates=ranked,
            leader=leader,
            comparison_complete=comparison_complete,
            target_health=int(target_health),
            target_resistance=float(target_resistance),
            target_name=target,
            evidence=evidence,
            unresolved=self._dedupe(unresolved),
        )


__all__ = [
    "ExtremeSustainedDPSComparisonCandidate",
    "ExtremeSustainedDPSComparisonResult",
    "ExtremeSustainedDPSComparisonService",
]
