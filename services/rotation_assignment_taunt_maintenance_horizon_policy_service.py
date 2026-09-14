from __future__ import annotations

"""Materialize reviewed symbolic taunt-maintenance policy from canonical encounter timing.

Provider ownership and reviewed strategy policy remain separate from fight-duration
mechanics. Symbolic policy may reference canonical health thresholds, encounter end, or
reviewed post-transition resume boundaries without persisting brittle absolute seconds.

A symbolic encounter policy may deliberately omit ``source_skill_name`` and bar. Those
are saved-build/provider facts, not encounter facts. Generate binds those facts from the
selected canonical provider and fails closed when the provider source is ambiguous.
"""

from dataclasses import dataclass
import math
import re

from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjection,
)
from services.rotation_assignment_taunt_maintenance_service import (
    RotationAssignmentTauntMaintenancePolicy,
    RotationAssignmentTauntMaintenanceWindow,
)
from services.rotation_tank_encounter_horizon_service import RotationTankEncounterHorizon
from services.rotation_tank_encounter_transition_timing_service import (
    RotationTankEncounterTransitionTiming,
)


_THRESHOLD_REFERENCE = re.compile(
    r"^health_threshold:(100|[1-9]?\d(?:\.\d+)?)%$",
    re.IGNORECASE,
)
_TRANSITION_RESUME_REFERENCE = re.compile(
    r"^transition_resume:(100|[1-9]?\d(?:\.\d+)?)%$",
    re.IGNORECASE,
)


def _fraction_from_reference(reference: str, pattern: re.Pattern[str]) -> float | None:
    match = pattern.fullmatch(str(reference or "").strip())
    if match is None:
        return None
    percent = float(match.group(1))
    if percent <= 0 or percent >= 100:
        raise ValueError("symbolic Tank timing percentage reference must be between 0% and 100%")
    return percent / 100.0


def _threshold_fraction(reference: str) -> float | None:
    return _fraction_from_reference(reference, _THRESHOLD_REFERENCE)


def _transition_resume_fraction(reference: str) -> float | None:
    return _fraction_from_reference(reference, _TRANSITION_RESUME_REFERENCE)


@dataclass(frozen=True)
class RotationAssignmentTauntMaintenanceHorizonWindow:
    occurrence_id: str
    target_key: str
    active_start_seconds: float | None = None
    start_reference: str | None = None
    end_reference: str = "encounter_end"
    bar: str | None = None

    def __post_init__(self) -> None:
        occurrence_id = str(self.occurrence_id or "").strip()
        target_key = str(self.target_key or "").strip()
        end_reference = str(self.end_reference or "").strip().casefold()
        if not occurrence_id:
            raise ValueError("symbolic taunt maintenance occurrence_id is required")
        if not target_key:
            raise ValueError("symbolic taunt maintenance target_key is required")
        if end_reference != "encounter_end" and _threshold_fraction(end_reference) is None:
            raise ValueError(
                "symbolic taunt maintenance end_reference must be 'encounter_end' or 'health_threshold:<percent>%'"
            )

        start_reference = (
            None if self.start_reference is None else str(self.start_reference or "").strip().casefold()
        )
        has_numeric_start = self.active_start_seconds is not None
        has_reference_start = start_reference is not None
        if has_numeric_start == has_reference_start:
            raise ValueError(
                "symbolic taunt maintenance window requires exactly one of active_start_seconds or start_reference"
            )
        if has_numeric_start:
            start = float(self.active_start_seconds)
            if not math.isfinite(start) or start < 0:
                raise ValueError(
                    "symbolic taunt maintenance active_start_seconds must be finite and non-negative"
                )
            object.__setattr__(self, "active_start_seconds", start)
        else:
            if _transition_resume_fraction(start_reference or "") is None:
                raise ValueError(
                    "symbolic taunt maintenance start_reference must be 'transition_resume:<percent>%'"
                )
            object.__setattr__(self, "start_reference", start_reference)

        object.__setattr__(self, "occurrence_id", occurrence_id)
        object.__setattr__(self, "target_key", target_key)
        object.__setattr__(self, "end_reference", end_reference)
        if self.bar is not None:
            bar = str(self.bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("symbolic taunt maintenance bar must be front or back")
            object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class RotationAssignmentTauntMaintenanceHorizonPolicy:
    requirement_id: str
    encounter_id: str
    requirement_type: str
    windows: tuple[RotationAssignmentTauntMaintenanceHorizonWindow, ...]
    source: str
    source_skill_name: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("requirement_id", "encounter_id", "requirement_type", "source"):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"symbolic taunt maintenance policy {field_name} must be non-empty")
            object.__setattr__(self, field_name, value)
        if self.source_skill_name is not None:
            source_skill_name = str(self.source_skill_name or "").strip()
            if not source_skill_name:
                raise ValueError(
                    "symbolic taunt maintenance policy source_skill_name must be non-empty when supplied"
                )
            object.__setattr__(self, "source_skill_name", source_skill_name)
        windows = tuple(self.windows)
        if not windows:
            raise ValueError("symbolic taunt maintenance policy requires at least one window")
        ids = [window.occurrence_id for window in windows]
        if len(ids) != len(set(ids)):
            raise ValueError("symbolic taunt maintenance policy cannot duplicate occurrence_id")
        object.__setattr__(self, "windows", windows)


@dataclass(frozen=True)
class RotationAssignmentTauntMaintenanceHorizonMaterialization:
    policy: RotationAssignmentTauntMaintenancePolicy | None
    resolved: bool
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


class RotationAssignmentTauntMaintenanceHorizonPolicyService:
    """Resolve symbolic encounter/threshold/transition timing into numeric maintenance."""

    @staticmethod
    def _raw_threshold_time(
        *,
        policy: RotationAssignmentTauntMaintenanceHorizonPolicy,
        window: RotationAssignmentTauntMaintenanceHorizonWindow,
        fraction: float,
        health_threshold_projection: EncounterHealthThresholdProjection | None,
    ) -> tuple[float | None, tuple[str, ...], tuple[str, ...]]:
        projection = health_threshold_projection
        if projection is None:
            return None, (), (
                f"{policy.requirement_id}:{window.occurrence_id}: canonical health-threshold projection is unavailable for {fraction * 100:g}% endpoint",
            )
        if projection.encounter_id != policy.encounter_id:
            raise ValueError(
                "Tank health-threshold projection encounter does not match symbolic taunt maintenance policy encounter"
            )
        matches = tuple(
            point
            for point in projection.points
            if math.isclose(float(point.threshold_fraction), fraction, rel_tol=0.0, abs_tol=1e-9)
        )
        if not matches:
            return None, (), (
                f"{policy.requirement_id}:{window.occurrence_id}: no canonical {fraction * 100:g}% health-threshold clock point is available",
            )
        unresolved_matches = tuple(
            point for point in matches if not point.resolved or point.time_seconds is None
        )
        if unresolved_matches:
            reasons = "; ".join(
                dict.fromkeys(str(point.reason or "unresolved threshold") for point in unresolved_matches)
            )
            return None, (), (
                f"{policy.requirement_id}:{window.occurrence_id}: canonical {fraction * 100:g}% health-threshold clock point is unresolved: {reasons}",
            )
        value = float(matches[0].time_seconds)
        if any(
            not math.isclose(float(point.time_seconds), value, rel_tol=0.0, abs_tol=1e-9)
            for point in matches[1:]
        ):
            return None, (), (
                f"{policy.requirement_id}:{window.occurrence_id}: corroborating {fraction * 100:g}% health-threshold facts disagree on projected clock time",
            )
        fact_keys = tuple(dict.fromkeys(str(point.fact_key) for point in matches))
        return value, tuple(f"threshold_fact={fact_key}" for fact_key in fact_keys), ()

    def _threshold_end(
        self,
        *,
        policy: RotationAssignmentTauntMaintenanceHorizonPolicy,
        window: RotationAssignmentTauntMaintenanceHorizonWindow,
        health_threshold_projection: EncounterHealthThresholdProjection | None,
        transition_timing: RotationTankEncounterTransitionTiming | None,
    ) -> tuple[float | None, tuple[str, ...], tuple[str, ...]]:
        fraction = _threshold_fraction(window.end_reference)
        if fraction is None:
            raise ValueError("threshold endpoint resolver requires a health-threshold reference")
        raw, fact_evidence, unresolved = self._raw_threshold_time(
            policy=policy,
            window=window,
            fraction=fraction,
            health_threshold_projection=health_threshold_projection,
        )
        if unresolved or raw is None:
            return None, (), unresolved
        adjusted = None
        if transition_timing is not None:
            if transition_timing.encounter_id != policy.encounter_id:
                raise ValueError(
                    "Tank transition timing encounter does not match symbolic taunt maintenance policy encounter"
                )
            adjusted = transition_timing.crossing_time_for(fraction)
        end = raw if adjusted is None else float(adjusted)
        return end, (
            f"symbolic_endpoint=health_threshold:{fraction * 100:g}%:{end:g}",
            *fact_evidence,
        ), ()

    @staticmethod
    def _window_start(
        *,
        policy: RotationAssignmentTauntMaintenanceHorizonPolicy,
        window: RotationAssignmentTauntMaintenanceHorizonWindow,
        transition_timing: RotationTankEncounterTransitionTiming | None,
    ) -> tuple[float | None, tuple[str, ...], tuple[str, ...]]:
        if window.active_start_seconds is not None:
            return float(window.active_start_seconds), (), ()
        fraction = _transition_resume_fraction(window.start_reference or "")
        if fraction is None:
            raise ValueError("symbolic transition start resolver requires transition_resume reference")
        timing = transition_timing
        if timing is None:
            return None, (), (
                f"{policy.requirement_id}:{window.occurrence_id}: reviewed transition timing is unavailable for {fraction * 100:g}% resume",
            )
        if timing.encounter_id != policy.encounter_id:
            raise ValueError(
                "Tank transition timing encounter does not match symbolic taunt maintenance policy encounter"
            )
        if not timing.resolved:
            return None, (), tuple(timing.unresolved) or (
                f"{policy.requirement_id}:{window.occurrence_id}: reviewed transition timing is unresolved",
            )
        start = timing.resume_time_for(fraction)
        if start is None:
            return None, (), (
                f"{policy.requirement_id}:{window.occurrence_id}: no reviewed {fraction * 100:g}% transition-resume boundary is available",
            )
        return float(start), (
            f"symbolic_start=transition_resume:{fraction * 100:g}%:{float(start):g}",
        ), ()

    def materialize(
        self,
        *,
        policy: RotationAssignmentTauntMaintenanceHorizonPolicy,
        horizon: RotationTankEncounterHorizon,
        health_threshold_projection: EncounterHealthThresholdProjection | None = None,
        transition_timing: RotationTankEncounterTransitionTiming | None = None,
        provider_source_skill_name: str | None = None,
        provider_source_bar: str | None = None,
    ) -> RotationAssignmentTauntMaintenanceHorizonMaterialization:
        if horizon.encounter_id != policy.encounter_id:
            raise ValueError(
                "Tank encounter horizon does not match symbolic taunt maintenance policy encounter"
            )

        reviewed_skill = None if policy.source_skill_name is None else str(policy.source_skill_name).strip()
        provider_skill = str(provider_source_skill_name or "").strip() or None
        if reviewed_skill and provider_skill and reviewed_skill.casefold() != provider_skill.casefold():
            return RotationAssignmentTauntMaintenanceHorizonMaterialization(
                policy=None,
                resolved=False,
                unresolved=(
                    f"{policy.requirement_id}: reviewed taunt skill {reviewed_skill!r} does not match canonical provider taunt {provider_skill!r}",
                ),
            )
        source_skill_name = reviewed_skill or provider_skill
        if not source_skill_name:
            return RotationAssignmentTauntMaintenanceHorizonMaterialization(
                policy=None,
                resolved=False,
                unresolved=(
                    f"{policy.requirement_id}: symbolic taunt-maintenance policy has no exact canonical provider taunt skill",
                ),
            )

        provider_bar = str(provider_source_bar or "").strip().casefold() or None
        if provider_bar is not None and provider_bar not in {"front", "back"}:
            raise ValueError("provider_source_bar must be front or back when supplied")

        if transition_timing is not None and transition_timing.encounter_id != policy.encounter_id:
            raise ValueError(
                "Tank transition timing encounter does not match symbolic taunt maintenance policy encounter"
            )

        windows: list[RotationAssignmentTauntMaintenanceWindow] = []
        timing_evidence: list[str] = []
        for window in policy.windows:
            start, start_evidence, unresolved = self._window_start(
                policy=policy,
                window=window,
                transition_timing=transition_timing,
            )
            if unresolved or start is None:
                return RotationAssignmentTauntMaintenanceHorizonMaterialization(
                    policy=None, resolved=False, unresolved=unresolved
                )

            if window.end_reference == "encounter_end":
                adjusted_end = (
                    None
                    if transition_timing is None
                    else transition_timing.adjusted_end_seconds
                )
                if adjusted_end is not None:
                    end = float(adjusted_end)
                    end_evidence = (f"symbolic_endpoint=encounter_end_adjusted:{end:g}",)
                else:
                    if not horizon.resolved or horizon.end_seconds is None:
                        return RotationAssignmentTauntMaintenanceHorizonMaterialization(
                            policy=None,
                            resolved=False,
                            unresolved=tuple(horizon.unresolved) or ("Tank encounter horizon is unresolved",),
                        )
                    end = float(horizon.end_seconds)
                    end_evidence = (f"symbolic_endpoint=encounter_end:{end:g}",)
            else:
                end, end_evidence, unresolved = self._threshold_end(
                    policy=policy,
                    window=window,
                    health_threshold_projection=health_threshold_projection,
                    transition_timing=transition_timing,
                )
                if unresolved or end is None:
                    return RotationAssignmentTauntMaintenanceHorizonMaterialization(
                        policy=None, resolved=False, unresolved=unresolved
                    )

            if end <= start:
                return RotationAssignmentTauntMaintenanceHorizonMaterialization(
                    policy=None,
                    resolved=False,
                    unresolved=(
                        f"{policy.requirement_id}:{window.occurrence_id}: projected symbolic endpoint does not occur after the reviewed maintenance start",
                    ),
                )
            if window.bar and provider_bar and window.bar != provider_bar:
                return RotationAssignmentTauntMaintenanceHorizonMaterialization(
                    policy=None,
                    resolved=False,
                    unresolved=(
                        f"{policy.requirement_id}:{window.occurrence_id}: reviewed taunt bar {window.bar!r} does not match canonical provider bar {provider_bar!r}",
                    ),
                )
            windows.append(
                RotationAssignmentTauntMaintenanceWindow(
                    occurrence_id=window.occurrence_id,
                    target_key=window.target_key,
                    active_start_seconds=start,
                    active_end_seconds=end,
                    bar=window.bar or provider_bar,
                )
            )
            timing_evidence.extend((*start_evidence, *end_evidence))

        materialized = RotationAssignmentTauntMaintenancePolicy(
            requirement_id=policy.requirement_id,
            encounter_id=policy.encounter_id,
            requirement_type=policy.requirement_type,
            source_skill_name=source_skill_name,
            windows=tuple(windows),
            source=policy.source,
        )
        return RotationAssignmentTauntMaintenanceHorizonMaterialization(
            policy=materialized,
            resolved=True,
            evidence=(
                *tuple(horizon.evidence),
                *(tuple(transition_timing.evidence) if transition_timing is not None else ()),
                *tuple(timing_evidence),
                f"provider_taunt={source_skill_name}",
                *(() if provider_bar is None else (f"provider_taunt_bar={provider_bar}",)),
            ),
        )


__all__ = [
    "RotationAssignmentTauntMaintenanceHorizonMaterialization",
    "RotationAssignmentTauntMaintenanceHorizonPolicy",
    "RotationAssignmentTauntMaintenanceHorizonPolicyService",
    "RotationAssignmentTauntMaintenanceHorizonWindow",
]
