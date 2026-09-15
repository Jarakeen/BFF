from __future__ import annotations

import ast
from pathlib import Path

from tools.audit_system_architecture import (
    _duplicate_class_findings,
    _install_fanout_findings,
    _legacy_generated_roster_alias_findings,
    _monkey_patch_findings,
    _quarantine_import_findings,
    _repo_contract_findings,
    audit_system_architecture,
)


def test_duplicate_class_detector_catches_shadowed_runtime_definition(tmp_path) -> None:
    path = tmp_path / "engine" / "operations.py"
    path.parent.mkdir(parents=True)
    source = "class Engine:\n    pass\n\nclass Engine:\n    pass\n"
    path.write_text(source, encoding="utf-8")

    findings = _duplicate_class_findings(tmp_path, path, ast.parse(source))

    assert len(findings) == 1
    assert findings[0].code == "duplicate-class-definition"
    assert "Engine is defined 2 times" in findings[0].message


def test_ui_audit_catches_class_monkey_patch_and_transitive_installer_fanout(tmp_path) -> None:
    path = tmp_path / "ui" / "feature_support.py"
    path.parent.mkdir(parents=True)
    source = """
def install():
    install_alpha()
    install_beta()
    install_gamma()
    install_delta()
    install_epsilon()
    Page.__init__ = replacement
"""
    tree = ast.parse(source)

    patches = _monkey_patch_findings(tmp_path, path, tree)
    fanout = _install_fanout_findings(tmp_path, path, tree)

    assert patches and patches[0].code == "ui-class-monkey-patch"
    assert "Page.__init__" in patches[0].message
    assert fanout and fanout[0].code == "installer-fanout"


def test_runtime_quarantine_imports_are_architecture_errors(tmp_path) -> None:
    path = tmp_path / "services" / "live_service.py"
    path.parent.mkdir(parents=True)
    source = """
from old_pages.old_math import calculate
from legacy.compat import OldThing
from deprecated.previous_service import PreviousService
from migration.v2_to_v3 import migrate
"""

    findings = _quarantine_import_findings(tmp_path, path, ast.parse(source))

    assert len(findings) == 1
    finding = findings[0]
    assert finding.severity == "ERROR"
    assert finding.code == "runtime-quarantine-import"
    assert "old_pages.old_math" in finding.message
    assert "legacy.compat" in finding.message
    assert "deprecated.previous_service" in finding.message
    assert "migration.v2_to_v3" in finding.message


def test_normal_runtime_imports_do_not_trigger_quarantine_boundary(tmp_path) -> None:
    path = tmp_path / "services" / "live_service.py"
    path.parent.mkdir(parents=True)
    source = """
from models.build_model import PlayerBuild
from services.roster_service import RosterService
"""

    assert _quarantine_import_findings(tmp_path, path, ast.parse(source)) == []


def test_live_generated_roster_plan_alias_import_is_reported(tmp_path) -> None:
    path = tmp_path / "ui" / "legacy_consumer.py"
    path.parent.mkdir(parents=True)
    source = """
from services.generated_roster_plan_service import (
    GeneratedRosterPlanService,
    GeneratedRosterPlanSlot,
)
"""

    findings = _legacy_generated_roster_alias_findings(
        tmp_path, path, ast.parse(source)
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.code == "legacy-generated-roster-plan-runtime-alias"
    assert "GeneratedRosterPlanService" in finding.message
    assert "GeneratedRosterPlanSlot" in finding.message


def test_generated_roster_draft_api_does_not_trigger_legacy_alias_finding(tmp_path) -> None:
    path = tmp_path / "ui" / "draft_consumer.py"
    path.parent.mkdir(parents=True)
    source = """
from services.generated_roster_plan_service import (
    GeneratedRosterDraftService,
    GeneratedRosterDraftSlot,
)
"""

    assert _legacy_generated_roster_alias_findings(
        tmp_path, path, ast.parse(source)
    ) == []


def test_repo_contract_detector_flags_hidden_build_persistence_authority(tmp_path) -> None:
    services = tmp_path / "services"
    services.mkdir(parents=True)
    (services / "__init__.py").write_text(
        "BuildService.load = load\nBuildService.save = save\n_install_build_persistence()\n",
        encoding="utf-8",
    )

    findings = _repo_contract_findings(tmp_path)
    codes = {row.code for row in findings}

    assert "build-persistence-authority-bypass" in codes
    assert "package-import-side-effect" in codes


def test_repo_contract_detector_flags_legacy_backed_generated_draft_storage(tmp_path) -> None:
    services = tmp_path / "services"
    services.mkdir(parents=True)
    (services / "raid_plan_repository.py").write_text("class RaidPlanRepository: pass\n", encoding="utf-8")
    (services / "generated_roster_plan_service.py").write_text(
        "class GeneratedRosterDraftService: pass\n",
        encoding="utf-8",
    )

    findings = _repo_contract_findings(tmp_path)
    assert "overlapping-plan-persistence" in {row.code for row in findings}


def test_current_repo_audit_confirms_resolved_authority_and_identity_debt() -> None:
    root = Path(__file__).resolve().parents[2]

    result = audit_system_architecture(root=root)
    codes = {row.code for row in result.findings}

    assert "build-persistence-authority-bypass" not in codes
    assert "package-import-side-effect" not in codes
    assert "raid-plan-name-based-build-identity" not in codes
    assert "stale-raid-plan-persistence-doc" not in codes
    assert "runtime-quarantine-import" not in codes
    assert "legacy-generated-roster-plan-runtime-alias" not in codes
    assert "catalog-family-transitive-aggregation" not in codes
    assert "duplicate-class-definition" not in codes
    assert "overlapping-plan-persistence" not in codes
    assert "runtime-local-data-path" not in codes
    assert "installer-fanout" not in codes
    assert "ui-class-monkey-patch" in codes
