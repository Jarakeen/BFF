from __future__ import annotations

"""Classify static build-context diagnostics for modeled DD output.

The shared BuildCalculationContext reports unresolved facts from many stat channels.
DD damage must fail closed for anything that can change modeled offensive output, but
it must not be blocked by diagnostics already proven irrelevant to that output.

This classifier is intentionally conservative. Only diagnostics whose irrelevance to
current DD damage math is established by the canonical mechanics layer are ambient.
Everything else remains relevant until a dedicated mechanic proves otherwise.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RotationDDOutputContextRelevance:
    relevant: tuple[str, ...]
    ambient: tuple[str, ...]

    @property
    def output_complete(self) -> bool:
        return not self.relevant


class RotationDDOutputContextRelevanceService:
    """Separate DD-output blockers from unrelated static-context diagnostics."""

    _AMBIENT_EXACT = frozenset(
        {
            "passive rank is not recorded for character: last gasp",
            "passive rank is not recorded for character: health avarice",
        }
    )

    _AMBIENT_SUBSTRINGS = (
        "champion point effect not yet modeled: master gatherer:",
        "champion point is dynamic or not yet stat-mapped: master gatherer",
        "champion point effect not yet modeled: celerity:",
        "champion point is dynamic or not yet stat-mapped: celerity",
        "movement_speed unresolved",
    )

    _STATIC_CONTEXT_PREFIXES = (
        "front static context:",
        "back static context:",
    )

    @classmethod
    def _classification_key(cls, message: str) -> str:
        key = str(message or "").strip().casefold()
        for prefix in cls._STATIC_CONTEXT_PREFIXES:
            if key.startswith(prefix):
                return key[len(prefix) :].strip()
        return key

    def classify(self, unresolved) -> RotationDDOutputContextRelevance:
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

        return RotationDDOutputContextRelevance(
            relevant=tuple(relevant),
            ambient=tuple(ambient),
        )


__all__ = [
    "RotationDDOutputContextRelevance",
    "RotationDDOutputContextRelevanceService",
]
