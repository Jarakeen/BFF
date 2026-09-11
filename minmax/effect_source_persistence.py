from __future__ import annotations

"""Canonical source-availability semantics for already-created effects.

This contract answers one narrow question: after an effect has legally activated,
does its source still need to remain active for the effect to contribute?

It does not decide whether the effect can trigger, how long it lasts, or whether a
bar-local set breakpoint exists. Those remain owned by trigger/runtime and gear
activation services.
"""

from enum import Enum


class EffectSourcePersistence(str, Enum):
    """How an activated effect depends on the source that created it."""

    PERSISTS_AFTER_ACTIVATION = "persists_after_activation"
    """The timed effect keeps running after its source becomes inactive."""

    REQUIRES_SOURCE_ACTIVE_AT_SNAPSHOT = "requires_source_active_at_snapshot"
    """The effect contributes only while its source is active at the snapshot."""

    ENDS_WHEN_SOURCE_INACTIVE = "ends_when_source_inactive"
    """Any source-inactive interval ends the activated effect window."""


__all__ = ["EffectSourcePersistence"]
