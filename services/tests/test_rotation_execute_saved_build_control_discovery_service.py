from types import SimpleNamespace

from services.rotation_execute_evidence_disposition_service import (
    RotationExecuteEvidenceDisposition,
    RotationExecuteEvidenceDispositionResult,
)
from services.rotation_execute_saved_build_control_discovery_service import (
    RotationExecuteSavedBuildControlDiscoveryService,
)


class _StubDispositionService:
    def resolve(self, skill_name: str) -> RotationExecuteEvidenceDispositionResult:
        if skill_name == "Execute":
            disposition = RotationExecuteEvidenceDisposition.THRESHOLD_ACTIVATION_SUPPORTED
        elif skill_name == "Continuous":
            disposition = RotationExecuteEvidenceDisposition.CONTINUOUS_AMPLIFICATION_UNRESOLVED
        else:
            disposition = RotationExecuteEvidenceDisposition.NO_THRESHOLD_EVIDENCE
        return RotationExecuteEvidenceDispositionResult(
            skill_name=skill_name,
            disposition=disposition,
            evidence=SimpleNamespace(resolved_skill_name=skill_name),
        )


def _build(name: str, role: str, front, back=()):
    return SimpleNamespace(
        Name=name,
        BuildName=f"{name} build",
        Role=role,
        FrontBarSkills=list(front),
        BackBarSkills=list(back),
    )


def test_discovery_returns_dd_builds_and_prioritizes_threshold_positive_controls() -> None:
    service = RotationExecuteSavedBuildControlDiscoveryService(
        disposition_service=_StubDispositionService(),
    )

    controls = service.discover(
        (
            _build("Negative", "DD", ("Filler",)),
            _build("Positive", "DD", ("Execute", "Filler")),
            _build("Healer", "Healer", ("Execute",)),
        )
    )

    assert [row.character_name for row in controls] == ["Positive", "Negative"]
    assert controls[0].is_positive_threshold_control is True
    assert controls[0].threshold_supported[0].skill_name == "Execute"
    assert controls[1].is_positive_threshold_control is False


def test_discovery_preserves_continuous_execute_as_unresolved_not_supported() -> None:
    service = RotationExecuteSavedBuildControlDiscoveryService(
        disposition_service=_StubDispositionService(),
    )

    control = service.discover((_build("Continuous DD", "DPS", ("Continuous",)),))[0]

    assert control.is_positive_threshold_control is False
    assert len(control.continuous_unresolved) == 1
    assert control.continuous_unresolved[0].skill_name == "Continuous"
