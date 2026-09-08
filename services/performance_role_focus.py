from __future__ import annotations

"""Role-aware Performance Dashboard defaults and calibrated working targets.

These values are presentation / coaching policy, not canonical ESO mechanics.
Calibrated targets come from reviewed user-supplied BTVTools examples and are
intentionally rounded into BFF working targets rather than copied verbatim.
Unknown effects fall back to incremental personal targets elsewhere.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceRoleProfile:
    Role: str
    CardTitle: str
    Intro: str
    TrackedEffects: tuple[str, ...]


_ROLE_PROFILES = {
    "healer": PerformanceRoleProfile(
        Role="Healer",
        CardTitle="Performance Focus",
        Intro="Suggestions are clues, not assignments. Pin only what is actually your job.",
        TrackedEffects=(
            "Major Brittle",
            "Minor Berserk",
            "Major Courage",
            "Major Slayer",
        ),
    ),
    "dps": PerformanceRoleProfile(
        Role="DPS",
        CardTitle="Damage Focus",
        Intro=(
            "Prioritize damage execution and self-maintained effects. Raid buffs are context, "
            "not automatically your personal responsibility."
        ),
        TrackedEffects=(
            "Major Berserk",
            "Major Slayer",
            "Major Force",
            "Minor Force",
            "Empower",
            "Major Courage",
        ),
    ),
    "tank": PerformanceRoleProfile(
        Role="Tank",
        CardTitle="Tank Focus",
        Intro=(
            "Prioritize boss control, debuffs, defensive coverage, and assigned group utility. "
            "Damage remains context, not the tank's report card."
        ),
        TrackedEffects=(
            "Major Breach",
            "Minor Breach",
            "Major Vulnerability",
            "Major Force",
            "Major Resolve",
            "Major Protection",
        ),
    ),
}


# Rounded BFF working targets calibrated from reviewed BTVTools examples.
# They remain encounter / assignment aware and must not be treated as universal constants.
_BFF_DESIRED_UPTIMES = {
    "major berserk": 95.0,
    "major slayer": 90.0,
    "powerful assault": 92.5,
    "minor courage": 95.0,
    "major vulnerability": 55.0,
    "off balance": 30.0,
}


def role_profile(role: str) -> PerformanceRoleProfile:
    return _ROLE_PROFILES.get(str(role or "").strip().casefold(), _ROLE_PROFILES["dps"])


def desired_uptime(name: str) -> float | None:
    return _BFF_DESIRED_UPTIMES.get(str(name or "").strip().casefold())


def desired_uptimes() -> dict[str, float]:
    return dict(_BFF_DESIRED_UPTIMES)
