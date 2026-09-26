from __future__ import annotations

from types import SimpleNamespace

from minmax.rotation_plan import RotationPlan
from models.build_model import BuildRoster, PlayerBuild
from services.extreme_sustained_dps_candidate_discovery_service import (
    ExtremeSustainedDPSCandidateDiscoveryService,
)


class _BuildService:
    def __init__(self, members):
        self._roster = BuildRoster(Members=list(members))

    def load(self):
        return self._roster


class _CatalogService:
    def __init__(self, build_ids):
        self._build_ids = set(build_ids)

    def load_strict(self):
        return SimpleNamespace(
            builds=tuple(
                SimpleNamespace(
                    build_id=build_id,
                    name=build_id,
                    payload={
                        "Name": build_id,
                        "BuildName": build_id,
                    },
                )
                for build_id in self._build_ids
            )
        )

    def load(self):
        return {
            "builds": tuple(
                {
                    "build_id": build_id,
                    "name": build_id,
                    "payload": {
                        "Name": build_id,
                        "BuildName": build_id,
                    },
                }
                for build_id in self._build_ids
            )
        }


class _ArtifactService:
    def __init__(self, plans):
        self.plans = dict(plans)

    def get_rotation_plan(self, build_id):
        value = self.plans.get(build_id)
        if isinstance(value, Exception):
            raise value
        return value


def _build(build_id: str, role: str, name: str) -> PlayerBuild:
    return PlayerBuild(
        Name="Tester",
        BuildName=name,
        BuildId=build_id,
        Role=role,
    )


def _plan(name: str, duration: float = 60.0) -> RotationPlan:
    return RotationPlan(
        character_name="Tester",
        build_name=name,
        duration_seconds=duration,
        actions=(),
    )


def test_discovery_includes_only_dd_builds_with_valid_saved_rotation() -> None:
    service = ExtremeSustainedDPSCandidateDiscoveryService(
        "data/eso.db",
        build_service=_BuildService(
            (
                _build("dd-good", "DD", "Good"),
                _build("heal", "Healer", "Heal"),
                _build("dd-missing", "DPS", "Missing"),
                _build("stale", "DD", "Stale"),
            )
        ),
        catalog_service=_CatalogService(("dd-good", "heal", "dd-missing")),
        artifact_service=_ArtifactService(
            {
                "dd-good": _plan("Good"),
                "heal": _plan("Heal"),
                "dd-missing": None,
            }
        ),
    )

    result = service.discover()

    assert result.candidate_count == 1
    assert result.candidates[0].build_id == "dd-good"
    assert result.candidates[0].rotation_duration_seconds == 60.0
    reasons = {row.build_id: row.reason for row in result.exclusions}
    assert "not explicitly DD/DPS role" in reasons["heal"]
    assert "no saved canonical RotationPlan" in reasons["dd-missing"]
    assert "identity is missing, stale, or ambiguous" in reasons["stale"]


def test_discovery_excludes_invalid_rotation_artifact_with_reason() -> None:
    service = ExtremeSustainedDPSCandidateDiscoveryService(
        "data/eso.db",
        build_service=_BuildService((_build("dd-bad", "DD", "Bad"),)),
        catalog_service=_CatalogService(("dd-bad",)),
        artifact_service=_ArtifactService(
            {"dd-bad": ValueError("rotation artifact action 2 is invalid")}
        ),
    )

    result = service.discover()

    assert result.candidate_count == 0
    assert len(result.exclusions) == 1
    assert result.exclusions[0].build_id == "dd-bad"
    assert "rotation artifact action 2 is invalid" in result.exclusions[0].reason
