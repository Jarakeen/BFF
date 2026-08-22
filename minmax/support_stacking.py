from enum import Enum


class StackingBehavior(str, Enum):
    """How repeated applications of a support effect interact with each other."""

    UNIQUE = "unique"
    """Only one instance can be active; a new application simply refreshes it."""

    STACKS = "stacks"
    """Multiple instances can be active at once and their magnitudes combine."""

    HIGHEST_ONLY = "highest_only"
    """Multiple sources may apply it, but only the strongest instance counts."""
