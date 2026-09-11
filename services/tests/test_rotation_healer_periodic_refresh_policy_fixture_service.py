from pathlib import Path
import json

from services.rotation_healer_periodic_refresh_policy_fixture_service import (
    RotationHealerPeriodicRefreshPolicyFixtureService,
)
from services.rotation_healer_periodic_runtime_evidence_service import (
    RotationHealerPeriodicRefreshPolicy,
    RotationHealerReviewedRuntimeObservation,
)


def _observation(name="Energy Orb", coefficient=1, version="U50"):
    return RotationHealerReviewedRuntimeObservation(
        source_name=name,
        coefficient_number=coefficient,
        first_tick_offset_seconds=0.041,
        tick_on_expiry_boundary=False,
        refresh_policy=None,
        provenance=("reviewed isolated timing",),
        game_version=version,
    )


def test_loads_reviewed_restart_fixture_and_composes_exact_identity(tmp_path: Path):
    path = tmp_path / "refresh.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "review_status": "reviewed",
                "game_version": "U50",
                "policies": [
                    {
                        "source_name": "Energy Orb",
                        "coefficient_number": 1,
                        "refresh_policy": "restart",
                        "provenance": ["reviewed cross-fight recipient-aware recast evidence"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    service = RotationHealerPeriodicRefreshPolicyFixtureService()
    fixture = service.load(path)
    result = service.compose((_observation(),), fixture)

    assert fixture.unresolved == ()
    assert result.unresolved == ()
    assert result.observations[0].refresh_policy is RotationHealerPeriodicRefreshPolicy.RESTART
    assert "reviewed refresh/recast policy: restart" in result.observations[0].provenance


def test_candidate_fixture_is_rejected(tmp_path: Path):
    path = tmp_path / "refresh.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "review_status": "candidate",
                "game_version": "U50",
                "policies": [],
            }
        ),
        encoding="utf-8",
    )

    try:
        RotationHealerPeriodicRefreshPolicyFixtureService().load(path)
    except ValueError as exc:
        assert "not reviewed" in str(exc)
    else:
        raise AssertionError("candidate refresh fixture must be rejected")


def test_unmatched_policy_fails_closed_during_composition(tmp_path: Path):
    path = tmp_path / "refresh.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "review_status": "reviewed",
                "game_version": "U50",
                "policies": [
                    {
                        "source_name": "Illustrious Healing",
                        "coefficient_number": 1,
                        "refresh_policy": "restart",
                        "provenance": ["reviewed evidence"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    service = RotationHealerPeriodicRefreshPolicyFixtureService()
    result = service.compose((_observation(),), service.load(path))

    assert result.observations[0].refresh_policy is None
    assert any("no matching reviewed runtime timing observation" in item for item in result.unresolved)


def test_duplicate_policy_identity_is_unresolved(tmp_path: Path):
    path = tmp_path / "refresh.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "review_status": "reviewed",
                "game_version": "U50",
                "policies": [
                    {
                        "source_name": "Energy Orb",
                        "coefficient_number": 1,
                        "refresh_policy": "restart",
                        "provenance": ["one"],
                    },
                    {
                        "source_name": "Energy Orb",
                        "coefficient_number": 1,
                        "refresh_policy": "restart",
                        "provenance": ["two"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    fixture = RotationHealerPeriodicRefreshPolicyFixtureService().load(path)
    assert len(fixture.policies) == 1
    assert any("duplicate refresh policy identity" in item for item in fixture.unresolved)
