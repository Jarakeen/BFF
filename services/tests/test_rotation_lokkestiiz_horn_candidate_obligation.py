from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_lokkestiiz_horn_candidate_obligation import (
    RotationLokkestiizHornCandidateObligation,
)
from services.rotation_lokkestiiz_landing_clock_service import (
    LokkestiizLandingClockEvidence,
)


def _plan(light_attack_times: tuple[float, ...]) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=40.0,
        actions=tuple(
            RotationAction(
                time_seconds=value,
                sequence=index,
                kind=RotationActionKind.LIGHT_ATTACK,
            )
            for index, value in enumerate(light_attack_times)
        ),
    )


def test_horn_candidate_obligation_returns_no_failure_when_all_landings_are_ready() -> None:
    resolver = RotationLokkestiizHornCandidateObligation(
        landing_clocks=LokkestiizLandingClockEvidence(
            landing_times_seconds=(10.0, 20.0, 30.0),
            sources=("pull", "pull", "pull"),
        ),
        starting_ultimate=750.0,
        horn_cost=250.0,
        assume_scheduled_attacks_damage=True,
    )

    assert resolver(_plan(())) == ()


def test_horn_candidate_obligation_returns_candidate_specific_failure() -> None:
    resolver = RotationLokkestiizHornCandidateObligation(
        landing_clocks=LokkestiizLandingClockEvidence(
            landing_times_seconds=(10.0, 20.0, 30.0),
            sources=("pull", "pull", "pull"),
        ),
        starting_ultimate=250.0,
        horn_cost=250.0,
        assume_scheduled_attacks_damage=True,
    )

    failures = resolver(_plan(()))

    assert any("landing 2" in item for item in failures)
    assert any("available=0.000" in item for item in failures)
