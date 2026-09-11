from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.rotation_healer_periodic_observation_fixture_service import (
    RotationHealerPeriodicObservationFixtureService,
)
from services.rotation_healer_periodic_refresh_policy_fixture_service import (
    RotationHealerPeriodicRefreshPolicyFixtureService,
)
from services.rotation_healer_periodic_runtime_evidence_service import (
    RotationHealerReviewedRuntimeObservation,
)


@dataclass(frozen=True)
class RotationHealerReviewedRuntimeEvidenceLoad:
    observations: tuple[RotationHealerReviewedRuntimeObservation, ...]
    unresolved: tuple[str, ...] = ()


class RotationHealerReviewedRuntimeEvidenceLoader:
    """Load reviewed healer timing evidence and optionally compose reviewed refresh policy.

    Isolated periodic timing and recast/refresh policy remain separate reviewed fixtures.
    This loader is the explicit consumer boundary that combines them. It performs no
    inference and never promotes candidate evidence.
    """

    def __init__(self, database_path: str | Path | None) -> None:
        self.database_path = (
            Path(database_path) if database_path is not None else None
        )
        self.refresh_fixtures = RotationHealerPeriodicRefreshPolicyFixtureService()

    def load(
        self,
        timing_fixture_path: str | Path | None,
        *,
        refresh_fixture_path: str | Path | None = None,
    ) -> RotationHealerReviewedRuntimeEvidenceLoad:
        if timing_fixture_path is None:
            unresolved = ()
            if refresh_fixture_path is not None:
                unresolved = (
                    "reviewed healer refresh policies were supplied without reviewed periodic timing evidence",
                )
            return RotationHealerReviewedRuntimeEvidenceLoad(
                observations=(),
                unresolved=unresolved,
            )

        if self.database_path is None:
            return RotationHealerReviewedRuntimeEvidenceLoad(
                observations=(),
                unresolved=(
                    "database path is required to load reviewed healer periodic timing evidence",
                ),
            )

        timing_fixtures = RotationHealerPeriodicObservationFixtureService(
            self.database_path
        )
        timing_report = timing_fixtures.load(timing_fixture_path)
        observations = tuple(timing_report.reviewed_observations)
        unresolved = list(timing_report.unresolved)

        if refresh_fixture_path is None:
            return RotationHealerReviewedRuntimeEvidenceLoad(
                observations=observations,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        refresh_report = self.refresh_fixtures.load(refresh_fixture_path)
        composition = self.refresh_fixtures.compose(observations, refresh_report)
        unresolved.extend(composition.unresolved)
        return RotationHealerReviewedRuntimeEvidenceLoad(
            observations=tuple(composition.observations),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "RotationHealerReviewedRuntimeEvidenceLoad",
    "RotationHealerReviewedRuntimeEvidenceLoader",
]
