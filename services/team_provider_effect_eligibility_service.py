from __future__ import annotations

from dataclasses import dataclass

from .team_provider_temporal_coverage_service import TeamProviderTimedApplication


def _canonical(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


def _canonical_tuple(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item for item in (_canonical(value) for value in values) if item))


@dataclass(frozen=True)
class EncounterEligibilityWindow:
    """One explicit encounter/runtime interval with semantic eligibility tags.

    These windows are inputs, not prose-derived encounter truth. Upstream encounter
    or log processing must establish the interval and its tags explicitly. Examples
    include ``boss_damageable``, ``adds_damageable``, ``raid_damage`` and
    ``transition_wait``. ``target_keys`` identify who can actually benefit during
    the interval when target identity matters.
    """

    window_key: str
    start_seconds: float
    end_seconds: float
    categories: tuple[str, ...]
    target_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _canonical(self.window_key):
            raise ValueError("window_key is required")
        if self.start_seconds < 0:
            raise ValueError("start_seconds cannot be negative")
        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        categories = _canonical_tuple(self.categories)
        if not categories:
            raise ValueError("at least one eligibility category is required")
        object.__setattr__(self, "categories", categories)
        object.__setattr__(self, "target_keys", _canonical_tuple(self.target_keys))


@dataclass(frozen=True)
class TeamProviderEffectEligibilityRule:
    """Define which encounter seconds belong in one effect's uptime denominator.

    Categories are OR-matched. When ``target_keys`` are supplied, a window must also
    explicitly name at least one matching target. Unspecified target identity is not
    treated as a match because that would silently convert missing evidence into
    eligibility.
    """

    effect_key: str
    eligible_categories: tuple[str, ...]
    target_keys: tuple[str, ...] = ()
    target_coverage_ratio: float = 1.0
    label: str = "effect eligibility"

    def __post_init__(self) -> None:
        effect_key = _canonical(self.effect_key)
        if not effect_key:
            raise ValueError("effect_key is required")
        categories = _canonical_tuple(self.eligible_categories)
        if not categories:
            raise ValueError("at least one eligible category is required")
        if not 0.0 < float(self.target_coverage_ratio) <= 1.0:
            raise ValueError("target_coverage_ratio must be greater than 0 and at most 1")
        object.__setattr__(self, "effect_key", effect_key)
        object.__setattr__(self, "eligible_categories", categories)
        object.__setattr__(self, "target_keys", _canonical_tuple(self.target_keys))


@dataclass(frozen=True)
class TeamProviderEligibleUptimeResult:
    effect_key: str
    eligible_seconds: float
    covered_seconds: float
    uncovered_seconds: float
    coverage_ratio: float
    target_coverage_ratio: float
    target_coverage_met: bool
    eligible_intervals: tuple[tuple[float, float], ...]
    covered_intervals: tuple[tuple[float, float], ...]
    matching_window_keys: tuple[str, ...]
    application_seconds_outside_eligible_windows: float


class TeamProviderEffectEligibilityService:
    """Evaluate provider uptime against effect-specific eligible encounter time."""

    @staticmethod
    def _merge(intervals: list[tuple[float, float]]) -> tuple[tuple[float, float], ...]:
        if not intervals:
            return ()
        ordered = sorted(intervals)
        merged: list[list[float]] = []
        for left, right in ordered:
            if not merged or left > merged[-1][1] + 1e-9:
                merged.append([left, right])
            else:
                merged[-1][1] = max(merged[-1][1], right)
        return tuple((left, right) for left, right in merged)

    @staticmethod
    def _duration(intervals: tuple[tuple[float, float], ...]) -> float:
        return sum(right - left for left, right in intervals)

    @classmethod
    def _window_matches(
        cls,
        rule: TeamProviderEffectEligibilityRule,
        window: EncounterEligibilityWindow,
    ) -> bool:
        if not set(rule.eligible_categories).intersection(window.categories):
            return False
        if not rule.target_keys:
            return True
        if not window.target_keys:
            return False
        return bool(set(rule.target_keys).intersection(window.target_keys))

    @classmethod
    def evaluate(
        cls,
        rule: TeamProviderEffectEligibilityRule,
        *,
        windows: tuple[EncounterEligibilityWindow, ...],
        applications: tuple[TeamProviderTimedApplication, ...],
    ) -> TeamProviderEligibleUptimeResult:
        matching_windows = tuple(window for window in windows if cls._window_matches(rule, window))
        eligible = cls._merge(
            [(float(window.start_seconds), float(window.end_seconds)) for window in matching_windows]
        )
        eligible_seconds = cls._duration(eligible)

        matching_applications = tuple(
            application
            for application in applications
            if _canonical(application.effect_key) == rule.effect_key
        )

        covered_pieces: list[tuple[float, float]] = []
        eligible_application_seconds = 0.0
        total_application_seconds = sum(
            float(application.duration_seconds) for application in matching_applications
        )
        for application in matching_applications:
            app_left = float(application.start_seconds)
            app_right = float(application.end_seconds)
            for eligible_left, eligible_right in eligible:
                left = max(app_left, eligible_left)
                right = min(app_right, eligible_right)
                if right <= left:
                    continue
                covered_pieces.append((left, right))
                eligible_application_seconds += right - left

        covered = cls._merge(covered_pieces)
        covered_seconds = cls._duration(covered)
        uncovered_seconds = max(0.0, eligible_seconds - covered_seconds)
        ratio = 0.0 if eligible_seconds <= 0 else covered_seconds / eligible_seconds
        target_met = eligible_seconds > 0 and ratio + 1e-9 >= float(rule.target_coverage_ratio)

        return TeamProviderEligibleUptimeResult(
            effect_key=rule.effect_key,
            eligible_seconds=eligible_seconds,
            covered_seconds=covered_seconds,
            uncovered_seconds=uncovered_seconds,
            coverage_ratio=ratio,
            target_coverage_ratio=float(rule.target_coverage_ratio),
            target_coverage_met=target_met,
            eligible_intervals=eligible,
            covered_intervals=covered,
            matching_window_keys=tuple(window.window_key for window in matching_windows),
            application_seconds_outside_eligible_windows=max(
                0.0,
                total_application_seconds - eligible_application_seconds,
            ),
        )
