from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtremeMaximumHealUnresolvedRelevanceResult:
    relevant: tuple[str, ...]
    ambient: tuple[str, ...]

    @property
    def objective_complete(self) -> bool:
        return not self.relevant


class ExtremeMaximumHealUnresolvedRelevanceService:
    """Classify diagnostics by whether they can affect maximum single-heal proof.

    This classifier is deliberately conservative. Unknown diagnostics remain
    objective-relevant. Only mechanics whose modeled domain cannot change the
    magnitude, recipient legality, activation legality, or event identity of a
    single healing event are downgraded to ambient build diagnostics.
    """

    _AMBIENT_SUBSTRINGS = (
        "champion point is dynamic or not yet stat-mapped: master gatherer",
        "champion point is dynamic or not yet stat-mapped: celerity",
        "movement_speed unresolved",
        "training: non-combat experience trait",
        "charged: requires status-effect chance model",
        "decisive: requires ultimate generation model",
    )

    def classify(self, unresolved) -> ExtremeMaximumHealUnresolvedRelevanceResult:
        relevant: list[str] = []
        ambient: list[str] = []
        for raw in tuple(unresolved or ()):
            message = str(raw or "").strip()
            if not message:
                continue
            key = message.casefold()
            if any(token in key for token in self._AMBIENT_SUBSTRINGS):
                ambient.append(message)
            else:
                relevant.append(message)
        return ExtremeMaximumHealUnresolvedRelevanceResult(
            relevant=tuple(dict.fromkeys(relevant)),
            ambient=tuple(dict.fromkeys(ambient)),
        )
