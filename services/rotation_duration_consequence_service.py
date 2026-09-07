from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_recast import RotationRecastSummary
from services.rotation_duration_analysis_service import RotationDurationProjection


@dataclass(frozen=True)
class RotationDurationConsequence:
    """One named duration-effect change between baseline and candidate schedules."""

    skill_name: str
    bar: str | None
    baseline: RotationRecastSummary | None
    candidate: RotationRecastSummary | None
    cast_count_delta: int | None
    active_seconds_delta: float | None
    uptime_fraction_delta: float | None
    total_gap_seconds_delta: float | None
    total_premature_seconds_delta: float | None
    unresolved: tuple[str, ...] = ()


class RotationDurationConsequenceService:
    """Compare canonical duration/recast evidence without inventing acceptability thresholds.

    This service deliberately does not decide whether a delay is acceptable gameplay.
    It reports what changed for caller-selected skills so a later encounter/support
    policy can impose explicit minimum uptime or maximum-gap obligations.
    """

    def compare(
        self,
        *,
        baseline: RotationDurationProjection,
        candidate: RotationDurationProjection,
        skills: tuple[tuple[str, str | None], ...],
    ) -> tuple[RotationDurationConsequence, ...]:
        seen: set[tuple[str, str | None]] = set()
        results: list[RotationDurationConsequence] = []

        for raw_name, raw_bar in skills:
            name = str(raw_name or "").strip()
            if not name:
                raise ValueError("rotation duration consequence skill name must be non-empty")
            bar = None if raw_bar is None else str(raw_bar).strip().casefold()
            if bar is not None and bar not in {"front", "back"}:
                raise ValueError("rotation duration consequence bar must be front, back, or None")

            key = (name.casefold(), bar)
            if key in seen:
                continue
            seen.add(key)

            base_summary = self._find_summary(baseline, name=name, bar=bar)
            candidate_summary = self._find_summary(candidate, name=name, bar=bar)
            unresolved: list[str] = []
            if base_summary is None:
                unresolved.append(
                    f"baseline duration evidence missing for {name!r} on {bar or 'any'} bar"
                )
            if candidate_summary is None:
                unresolved.append(
                    f"candidate duration evidence missing for {name!r} on {bar or 'any'} bar"
                )

            if base_summary is None or candidate_summary is None:
                results.append(
                    RotationDurationConsequence(
                        skill_name=name,
                        bar=bar,
                        baseline=base_summary,
                        candidate=candidate_summary,
                        cast_count_delta=None,
                        active_seconds_delta=None,
                        uptime_fraction_delta=None,
                        total_gap_seconds_delta=None,
                        total_premature_seconds_delta=None,
                        unresolved=tuple(unresolved),
                    )
                )
                continue

            results.append(
                RotationDurationConsequence(
                    skill_name=name,
                    bar=bar,
                    baseline=base_summary,
                    candidate=candidate_summary,
                    cast_count_delta=int(candidate_summary.cast_count - base_summary.cast_count),
                    active_seconds_delta=float(
                        candidate_summary.active_seconds - base_summary.active_seconds
                    ),
                    uptime_fraction_delta=float(
                        candidate_summary.uptime_fraction - base_summary.uptime_fraction
                    ),
                    total_gap_seconds_delta=float(
                        candidate_summary.total_gap_seconds - base_summary.total_gap_seconds
                    ),
                    total_premature_seconds_delta=float(
                        candidate_summary.total_premature_seconds
                        - base_summary.total_premature_seconds
                    ),
                    unresolved=(),
                )
            )

        return tuple(results)

    @staticmethod
    def _find_summary(
        projection: RotationDurationProjection,
        *,
        name: str,
        bar: str | None,
    ) -> RotationRecastSummary | None:
        matches = tuple(
            summary
            for summary in projection.analysis.summaries
            if summary.skill_name.casefold() == name.casefold()
            and (bar is None or summary.bar == bar)
        )
        if len(matches) > 1 and bar is None:
            raise ValueError(
                f"duration consequence comparison for {name!r} is ambiguous across bars"
            )
        return matches[0] if matches else None
