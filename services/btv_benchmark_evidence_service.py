from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .team_provider_temporal_coverage_service import TeamProviderTemporalCoverageResult
from .team_provider_uptime_policy_service import (
    TeamProviderUptimeAssessment,
    TeamProviderUptimePolicy,
    TeamProviderUptimePolicyService,
)


UPTIME_DENOMINATOR_UNKNOWN = "unknown"
UPTIME_DENOMINATOR_FULL_ENCOUNTER = "full_encounter"
UPTIME_DENOMINATOR_DAMAGEABLE_BOSS_TIME = "damageable_boss_time"
UPTIME_DENOMINATOR_PHASE_ACTIVE_TIME = "phase_active_time"
_ALLOWED_DENOMINATORS = {
    UPTIME_DENOMINATOR_UNKNOWN,
    UPTIME_DENOMINATOR_FULL_ENCOUNTER,
    UPTIME_DENOMINATOR_DAMAGEABLE_BOSS_TIME,
    UPTIME_DENOMINATOR_PHASE_ACTIVE_TIME,
}


def btv_uptime_denominator_from_exclude_downtime_toggle(
    exclude_downtime: bool | None,
) -> str:
    """Translate the visible BTVTools ``Exclude Downtime`` toggle into a denominator.

    The supplied screenshots show the top-right toggle as the denominator control.
    Purple/on means downtime such as boss immunity is excluded from the uptime
    denominator; dark/off means the full encounter window is used. When the toggle
    is cropped out or otherwise unreadable, preserve ``unknown`` rather than guess.
    """
    if exclude_downtime is True:
        return UPTIME_DENOMINATOR_DAMAGEABLE_BOSS_TIME
    if exclude_downtime is False:
        return UPTIME_DENOMINATOR_FULL_ENCOUNTER
    return UPTIME_DENOMINATOR_UNKNOWN


@dataclass(frozen=True)
class BTVBenchmarkObservation:
    """One screenshot-backed BTVTools benchmark observation.

    This is calibration evidence, not canonical ESO mechanic truth. Scope,
    provenance, and the uptime denominator are therefore part of the value rather
    than optional decoration. In particular, an uptime percentage measured across
    the full encounter is not comparable to one that excludes boss immunity or
    invulnerability time.
    """

    encounter_key: str
    encounter_label: str
    effect_key: str
    page: str
    observed_ratio: float | None
    target_ratio: float | None
    reference_average_ratio: float | None
    theoretical_max_ratio: float | None
    contribution_percent: float | None
    player_role: str | None
    source_file: str
    source: str
    uptime_denominator_basis: str = UPTIME_DENOMINATOR_UNKNOWN
    note: str = ""

    def __post_init__(self) -> None:
        for name in (
            "observed_ratio",
            "target_ratio",
            "reference_average_ratio",
            "theoretical_max_ratio",
        ):
            value = getattr(self, name)
            if value is not None and not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1 when supplied")
        if not self.encounter_key.strip():
            raise ValueError("encounter_key is required")
        if not self.effect_key.strip():
            raise ValueError("effect_key is required")
        if not self.page.strip():
            raise ValueError("page is required")
        if not self.source_file.strip():
            raise ValueError("source_file is required")
        if not self.source.strip():
            raise ValueError("source is required")
        if self.uptime_denominator_basis not in _ALLOWED_DENOMINATORS:
            raise ValueError(
                "uptime_denominator_basis must be one of: "
                + ", ".join(sorted(_ALLOWED_DENOMINATORS))
            )
        if (
            self.target_ratio is not None
            and self.theoretical_max_ratio is not None
            and self.target_ratio > self.theoretical_max_ratio + 1e-9
        ):
            raise ValueError(
                "target_ratio cannot exceed theoretical_max_ratio in benchmark evidence"
            )

    @property
    def excludes_boss_immunity_time(self) -> bool | None:
        if self.uptime_denominator_basis == UPTIME_DENOMINATOR_DAMAGEABLE_BOSS_TIME:
            return True
        if self.uptime_denominator_basis == UPTIME_DENOMINATOR_FULL_ENCOUNTER:
            return False
        return None

    @property
    def scope_key(self) -> tuple[str, str, str | None, str]:
        return (
            self.encounter_key.casefold(),
            self.page.casefold(),
            self.player_role.casefold() if self.player_role else None,
            self.effect_key.casefold(),
        )

    def comparable_uptime_with(self, other: "BTVBenchmarkObservation") -> bool:
        """Return True only when two uptime ratios share a known denominator basis.

        Unknown denominator evidence stays usable as provenance/calibration, but it
        may not be numerically ranked against another observation until the source
        denominator is established. Full-encounter and damageable-boss-time ratios
        are intentionally incomparable without an explicit normalization step.
        """
        if self.uptime_denominator_basis == UPTIME_DENOMINATOR_UNKNOWN:
            return False
        if other.uptime_denominator_basis == UPTIME_DENOMINATOR_UNKNOWN:
            return False
        return self.uptime_denominator_basis == other.uptime_denominator_basis

    def to_uptime_policy(self) -> TeamProviderUptimePolicy | None:
        """Project screenshot evidence into runtime policy only when a target exists."""
        if self.target_ratio is None:
            return None
        denominator_note = (
            f"uptime denominator={self.uptime_denominator_basis}; "
            "boss-immunity exclusion must be known before cross-source comparison. "
        )
        return TeamProviderUptimePolicy(
            effect_key=self.effect_key,
            target_ratio=self.target_ratio,
            encounter_key=self.encounter_key,
            theoretical_max_ratio=self.theoretical_max_ratio,
            source=f"{self.source}: {self.source_file}",
            note=denominator_note + self.note,
        )


@dataclass(frozen=True)
class BTVBenchmarkCorpus:
    schema_version: int
    encounter_key: str
    encounter_label: str
    source: str
    default_uptime_denominator_basis: str
    observations: tuple[BTVBenchmarkObservation, ...]

    def find(
        self,
        *,
        effect_key: str | None = None,
        page: str | None = None,
        player_role: str | None = None,
    ) -> tuple[BTVBenchmarkObservation, ...]:
        effect = str(effect_key or "").strip().casefold()
        page_key = str(page or "").strip().casefold()
        role_key = str(player_role or "").strip().casefold()
        return tuple(
            row
            for row in self.observations
            if (not effect or row.effect_key.casefold() == effect)
            and (not page_key or row.page.casefold() == page_key)
            and (
                not role_key
                or (row.player_role is not None and row.player_role.casefold() == role_key)
            )
        )


@dataclass(frozen=True)
class BTVBenchmarkTemporalAssessment:
    """Calibration feedback for one existing provider-temporal coverage result."""

    observation: BTVBenchmarkObservation
    temporal_result: TeamProviderTemporalCoverageResult
    uptime_assessment: TeamProviderUptimeAssessment | None
    benchmark_observed_comparison_allowed: bool
    benchmark_observed_delta_ratio: float | None
    theoretical_excess_ratio: float | None
    feedback: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def target_met(self) -> bool | None:
        if self.uptime_assessment is None:
            return None
        return self.uptime_assessment.target_met


class BTVBenchmarkEvidenceService:
    """Load, validate, and assess scoped BTVTools screenshot benchmark fixtures."""

    SCHEMA_VERSION = 1

    @staticmethod
    def _canonical(value: object) -> str:
        return "_".join(str(value or "").strip().casefold().replace("-", " ").split())

    @classmethod
    def load(cls, path: str | Path) -> BTVBenchmarkCorpus:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("BTV benchmark fixture must be a JSON object")
        schema_version = int(payload.get("schema_version", 0))
        if schema_version != cls.SCHEMA_VERSION:
            raise ValueError(
                f"unsupported BTV benchmark schema {schema_version}; expected {cls.SCHEMA_VERSION}"
            )
        encounter_key = str(payload.get("encounter_key") or "").strip()
        encounter_label = str(payload.get("encounter_label") or "").strip()
        source = str(payload.get("source") or "").strip()
        if not encounter_key or not encounter_label or not source:
            raise ValueError(
                "BTV benchmark fixture requires encounter_key, encounter_label, and source"
            )

        rules = payload.get("rules") if isinstance(payload.get("rules"), dict) else {}
        default_denominator = str(
            rules.get("uptime_denominator_basis") or UPTIME_DENOMINATOR_UNKNOWN
        ).strip()
        if default_denominator not in _ALLOWED_DENOMINATORS:
            raise ValueError("unsupported default uptime denominator basis")

        raw_rows = payload.get("observations")
        if not isinstance(raw_rows, list):
            raise ValueError("BTV benchmark fixture observations must be a list")

        observations: list[BTVBenchmarkObservation] = []
        for raw in raw_rows:
            if not isinstance(raw, dict):
                raise ValueError("every BTV benchmark observation must be an object")
            if "exclude_downtime_toggle" in raw:
                toggle_value = raw.get("exclude_downtime_toggle")
                if toggle_value not in (True, False, None):
                    raise ValueError(
                        "exclude_downtime_toggle must be true, false, or null when supplied"
                    )
                denominator = btv_uptime_denominator_from_exclude_downtime_toggle(
                    toggle_value
                )
            else:
                denominator = str(
                    raw.get("uptime_denominator_basis") or default_denominator
                ).strip()
            observations.append(
                BTVBenchmarkObservation(
                    encounter_key=encounter_key,
                    encounter_label=encounter_label,
                    effect_key=str(raw.get("effect_key") or "").strip(),
                    page=str(raw.get("page") or "").strip(),
                    observed_ratio=raw.get("observed_ratio"),
                    target_ratio=raw.get("target_ratio"),
                    reference_average_ratio=raw.get("reference_average_ratio"),
                    theoretical_max_ratio=raw.get("theoretical_max_ratio"),
                    contribution_percent=raw.get("contribution_percent"),
                    player_role=(
                        str(raw.get("player_role")).strip()
                        if raw.get("player_role") is not None
                        else None
                    ),
                    source_file=str(raw.get("source_file") or "").strip(),
                    source=source,
                    uptime_denominator_basis=denominator,
                    note=str(raw.get("note") or "").strip(),
                )
            )

        return BTVBenchmarkCorpus(
            schema_version=schema_version,
            encounter_key=encounter_key,
            encounter_label=encounter_label,
            source=source,
            default_uptime_denominator_basis=default_denominator,
            observations=tuple(observations),
        )

    @classmethod
    def select_target_observation(
        cls,
        corpus: BTVBenchmarkCorpus,
        *,
        effect_key: str,
        page: str = "insights",
        player_role: str | None = None,
    ) -> BTVBenchmarkObservation | None:
        """Return one unambiguous target-bearing row for the requested scope."""
        rows = corpus.find(
            effect_key=effect_key,
            page=page,
            player_role=player_role,
        )
        candidates = tuple(row for row in rows if row.target_ratio is not None)
        if not candidates:
            return None
        if len(candidates) > 1:
            scopes = ", ".join(
                f"{row.page}/{row.player_role or 'group'}:{row.source_file}"
                for row in candidates
            )
            raise ValueError(
                f"ambiguous BTV benchmark target for {effect_key!r}: {scopes}"
            )
        return candidates[0]

    @classmethod
    def assess_temporal_result(
        cls,
        observation: BTVBenchmarkObservation,
        temporal_result: TeamProviderTemporalCoverageResult,
        *,
        temporal_uptime_denominator_basis: str = UPTIME_DENOMINATOR_UNKNOWN,
    ) -> BTVBenchmarkTemporalAssessment:
        """Apply benchmark policy to an existing temporal-coverage result.

        Timing math remains owned by ``TeamProviderTemporalCoverageService``. This
        method only interprets that result against screenshot-backed calibration
        evidence and refuses cross-source observed-uptime comparison unless both
        denominator bases are known and equal.
        """
        if cls._canonical(observation.effect_key) != cls._canonical(
            temporal_result.effect_key
        ):
            raise ValueError(
                "benchmark effect_key must match temporal coverage effect_key"
            )
        if temporal_uptime_denominator_basis not in _ALLOWED_DENOMINATORS:
            raise ValueError("unsupported temporal uptime denominator basis")

        policy = observation.to_uptime_policy()
        uptime_assessment = None
        if policy is not None:
            uptime_assessment = TeamProviderUptimePolicyService.assess(
                policy,
                observed_ratio=temporal_result.coverage_ratio,
            )

        theoretical_excess = None
        if observation.theoretical_max_ratio is not None:
            theoretical_excess = max(
                0.0,
                float(temporal_result.coverage_ratio)
                - float(observation.theoretical_max_ratio),
            )

        same_known_denominator = (
            observation.uptime_denominator_basis != UPTIME_DENOMINATOR_UNKNOWN
            and temporal_uptime_denominator_basis != UPTIME_DENOMINATOR_UNKNOWN
            and observation.uptime_denominator_basis
            == temporal_uptime_denominator_basis
        )
        observed_delta = None
        if same_known_denominator and observation.observed_ratio is not None:
            observed_delta = (
                float(temporal_result.coverage_ratio)
                - float(observation.observed_ratio)
            )

        feedback: list[str] = []
        unresolved: list[str] = []
        planned_percent = temporal_result.coverage_ratio * 100.0

        if uptime_assessment is not None:
            target_percent = uptime_assessment.policy.target_percent
            if uptime_assessment.target_met:
                feedback.append(
                    f"Planned {observation.effect_key} uptime {planned_percent:.1f}% meets "
                    f"the scoped BTV target {target_percent:.1f}%."
                )
            else:
                feedback.append(
                    f"Planned {observation.effect_key} uptime {planned_percent:.1f}% is "
                    f"{uptime_assessment.shortfall_percent:.1f} percentage points below "
                    f"the scoped BTV target {target_percent:.1f}%."
                )
        elif observation.theoretical_max_ratio is not None:
            feedback.append(
                f"BTV provides no target for {observation.effect_key}; the visible "
                f"theoretical maximum is {observation.theoretical_max_ratio * 100.0:.1f}%."
            )
        else:
            unresolved.append(
                "Benchmark row has neither a target ratio nor a theoretical maximum."
            )

        if temporal_result.uncovered_intervals:
            rendered_gaps = ", ".join(
                f"{left:.1f}-{right:.1f}s"
                for left, right in temporal_result.uncovered_intervals
            )
            feedback.append(
                f"Uncovered provider time totals {temporal_result.uncovered_seconds:.1f}s "
                f"across {rendered_gaps}."
            )
        else:
            feedback.append("No uncovered provider time remains in the required window.")

        if temporal_result.simultaneous_overlap_seconds > 1e-9:
            feedback.append(
                f"Provider applications overlap for "
                f"{temporal_result.simultaneous_overlap_seconds:.1f}s; overlap is reported "
                "as a diagnostic and is not automatically treated as waste."
            )

        if theoretical_excess is not None and theoretical_excess > 1e-9:
            unresolved.append(
                f"Planned uptime exceeds the screenshot theoretical maximum by "
                f"{theoretical_excess * 100.0:.1f} percentage points; denominator or "
                "scope evidence must be reconciled before comparison."
            )

        if observation.observed_ratio is not None and not same_known_denominator:
            unresolved.append(
                "Screenshot-observed uptime is not numerically compared with BFF planned "
                "uptime because the two denominator bases are not both known and equal."
            )
        elif observed_delta is not None:
            direction = "above" if observed_delta >= 0 else "below"
            feedback.append(
                f"Planned uptime is {abs(observed_delta) * 100.0:.1f} percentage points "
                f"{direction} the screenshot observation on the same denominator basis."
            )

        return BTVBenchmarkTemporalAssessment(
            observation=observation,
            temporal_result=temporal_result,
            uptime_assessment=uptime_assessment,
            benchmark_observed_comparison_allowed=same_known_denominator,
            benchmark_observed_delta_ratio=observed_delta,
            theoretical_excess_ratio=theoretical_excess,
            feedback=tuple(feedback),
            unresolved=tuple(unresolved),
        )
