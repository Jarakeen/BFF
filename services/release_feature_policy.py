from __future__ import annotations

"""Release-only feature visibility policy for FoundryDock.

Development builds keep active work visible. Frozen release builds expose only routes that
have been approved in RELEASE_STATUS.md. The optional environment override exists for
release smoke tests from a source checkout.
"""

import os
import sys


# User-facing routes that remain active development work and therefore must not be
# exposed from a packaged release until their release status is explicitly promoted.
RELEASE_HIDDEN_ROUTES: frozenset[str] = frozenset(
    {
        "rotations",
        "extreme_optimization",
        "console:6",  # Optimizer Adviser / transition workspace
    }
)

# No currently approved release feature needs a hidden route prefix. Keep the tuple
# as the policy hook for future families of development-only deep links.
RELEASE_HIDDEN_ROUTE_PREFIXES: tuple[str, ...] = ()


def release_mode() -> bool:
    """Return True for a packaged release or an explicit source-checkout smoke test."""
    override = os.environ.get("FOUNDRYDOCK_RELEASE_MODE", "").strip().casefold()
    if override in {"1", "true", "yes", "on"}:
        return True
    if override in {"0", "false", "no", "off"}:
        return False
    return bool(getattr(sys, "frozen", False))


def route_allowed(route: str) -> bool:
    """Return whether a route is visible in the current runtime channel."""
    if not release_mode():
        return True
    clean = str(route or "").strip()
    if clean in RELEASE_HIDDEN_ROUTES:
        return False
    return not any(clean.startswith(prefix) for prefix in RELEASE_HIDDEN_ROUTE_PREFIXES)


__all__ = [
    "RELEASE_HIDDEN_ROUTES",
    "RELEASE_HIDDEN_ROUTE_PREFIXES",
    "release_mode",
    "route_allowed",
]
