from __future__ import annotations

"""Classify static build-context diagnostics for modeled healer output.

A shared ``BuildCalculationContext`` carries unresolved diagnostics from many stat
channels. Rotation healer output must not fail merely because an unrelated channel
such as movement speed or resistance is incomplete, but it also must not discard an
unknown that could change healing potency or runtime state.

This classifier is therefore deliberately small and fail-closed: only diagnostics
whose irrelevance to modeled healing-event magnitude is already established by the
canonical mechanics layer are treated as ambient. Every other diagnostic remains
relevant until another service proves otherwise.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RotationHealerOutputContextRelevance:
    relevant: tuple[str, ...]
    ambient: tuple[str, ...]

    @property
    def output_complete(self) -> bool:
        return not self.relevant


class RotationHealerOutputContextRelevanceService:
    """Separate healer-output blockers from unrelated static-context diagnostics."""

    _AMBIENT_EXACT = frozenset(
        {
            "passive rank is not recorded for character: flourish",
            "passive rank is not recorded for character: advanced species",
            "passive rank is not recorded for character: frozen armor",
        }
    )

    _AMBIENT_SUBSTRINGS = (
        "champion point is dynamic or not yet stat-mapped: master gatherer",
        "champion point is dynamic or not yet stat-mapped: celerity",
        "movement_speed unresolved",
    )

    _STATIC_CONTEXT_PREFIXES = (
        "front static context:",
        "back static context:",
    )

    @classmethod
    def _classification_key(cls, message: str) -> str:
        """Strip orchestration-only bar prefixes before mechanics classification.

        The original diagnostic text is preserved in the returned result. Only the
        comparison key is normalized so a front/back label cannot change whether the
        underlying mechanic is relevant to modeled healer output.
        """
        key = str(message or "").strip().casefold()
        for prefix in cls._STATIC_CONTEXT_PREFIXES:
            if key.startswith(prefix):
                return key[len(prefix) :].strip()
        return key

    def classify(self, unresolved) -> RotationHealerOutputContextRelevance:
        relevant: list[str] = []
        ambient: list[str] = []
        seen: set[str] = set()

        for raw in tuple(unresolved or ()):
            message = str(raw or "").strip()
            if not message:
                continue
            dedupe_key = message.casefold()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            key = self._classification_key(message)
            if key in self._AMBIENT_EXACT or any(
                token in key for token in self._AMBIENT_SUBSTRINGS
            ):
                ambient.append(message)
            else:
                relevant.append(message)

        return RotationHealerOutputContextRelevance(
            relevant=tuple(relevant),
            ambient=tuple(ambient),
        )


__all__ = [
    "RotationHealerOutputContextRelevance",
    "RotationHealerOutputContextRelevanceService",
]
