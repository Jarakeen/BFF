from __future__ import annotations

from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class TeamProviderCoverageProfile:
    """Coverage capacity for one team-facing provider mechanic.

    ``targets_per_application`` counts every recipient affected by one application,
    including the provider when the mechanic buffs the provider plus nearby allies.
    ``max_applications_per_cycle`` limits how many distinct applications can
    contribute concurrent/required coverage in one refresh cycle. Leave it None
    when repeated applications may continue covering additional recipients.

    This deliberately models capacity separately from named-buff stacking. A team
    can own a valid provider and still fail raid coverage because one application
    reaches only part of the intended recipient set.
    """

    provider_key: str
    targets_per_application: int
    max_applications_per_cycle: int | None = None
    application_label: str = "application"

    def __post_init__(self) -> None:
        if not str(self.provider_key or "").strip():
            raise ValueError("provider_key is required")
        if self.targets_per_application <= 0:
            raise ValueError("targets_per_application must be positive")
        if self.max_applications_per_cycle is not None and self.max_applications_per_cycle <= 0:
            raise ValueError("max_applications_per_cycle must be positive when supplied")


@dataclass(frozen=True)
class TeamProviderCoverageResult:
    provider_key: str
    required_recipients: int
    targets_per_application: int
    applications_needed: int
    applications_available: int
    applications_used: int
    covered_recipients: int
    uncovered_recipients: int
    application_label: str

    @property
    def fully_covered(self) -> bool:
        return self.uncovered_recipients == 0

    @property
    def coverage_ratio(self) -> float:
        if self.required_recipients <= 0:
            return 1.0
        return self.covered_recipients / self.required_recipients


class TeamProviderCoverageService:
    """Evaluate whether one provider can cover the intended team recipients."""

    @staticmethod
    def evaluate(
        profile: TeamProviderCoverageProfile,
        *,
        required_recipients: int,
    ) -> TeamProviderCoverageResult:
        required = int(required_recipients)
        if required < 0:
            raise ValueError("required_recipients cannot be negative")
        if required == 0:
            return TeamProviderCoverageResult(
                provider_key=profile.provider_key,
                required_recipients=0,
                targets_per_application=profile.targets_per_application,
                applications_needed=0,
                applications_available=0,
                applications_used=0,
                covered_recipients=0,
                uncovered_recipients=0,
                application_label=profile.application_label,
            )

        needed = ceil(required / profile.targets_per_application)
        available = (
            needed
            if profile.max_applications_per_cycle is None
            else profile.max_applications_per_cycle
        )
        used = min(needed, available)
        covered = min(required, used * profile.targets_per_application)
        return TeamProviderCoverageResult(
            provider_key=profile.provider_key,
            required_recipients=required,
            targets_per_application=profile.targets_per_application,
            applications_needed=needed,
            applications_available=available,
            applications_used=used,
            covered_recipients=covered,
            uncovered_recipients=max(0, required - covered),
            application_label=profile.application_label,
        )

    @staticmethod
    def combine(
        profiles: tuple[TeamProviderCoverageProfile, ...],
        *,
        required_recipients: int,
    ) -> TeamProviderCoverageResult:
        """Combine multiple independent providers of the same required effect.

        Each provider contributes only its own maximum distinct-recipient capacity.
        This is intentionally a capacity upper bound; actual target selection,
        positioning, timing, and overlap belong to later encounter/runtime planning.
        """
        required = int(required_recipients)
        if required < 0:
            raise ValueError("required_recipients cannot be negative")
        if not profiles:
            return TeamProviderCoverageResult(
                provider_key="combined",
                required_recipients=required,
                targets_per_application=0,
                applications_needed=0 if required == 0 else required,
                applications_available=0,
                applications_used=0,
                covered_recipients=0,
                uncovered_recipients=required,
                application_label="application",
            )

        capacities = []
        available_applications = 0
        for profile in profiles:
            max_apps = profile.max_applications_per_cycle
            if max_apps is None:
                max_apps = ceil(required / profile.targets_per_application) if required else 0
            available_applications += max_apps
            capacities.append(profile.targets_per_application * max_apps)

        covered = min(required, sum(capacities))
        return TeamProviderCoverageResult(
            provider_key="combined",
            required_recipients=required,
            targets_per_application=max(profile.targets_per_application for profile in profiles),
            applications_needed=0 if required == 0 else 1,
            applications_available=available_applications,
            applications_used=available_applications,
            covered_recipients=covered,
            uncovered_recipients=max(0, required - covered),
            application_label="application",
        )
