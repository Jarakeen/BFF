from __future__ import annotations

import ast
from pathlib import Path

from tools.audit_system_architecture import (
    _duplicate_class_findings,
    _install_fanout_findings,
    _monkey_patch_findings,
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


def test_current_repo_audit_confirms_resolved_authority_and_identity_debt() -> None:
    root = Path(__file__).resolve().parents[2]

    result = audit_system_architecture(root=root)
    codes = {row.code for row in result.findings}

    assert "build-persistence-authority-bypass" not in codes
    assert "package-import-side-effect" not in codes
    assert "raid-plan-name-based-build-identity" not in codes
    assert "stale-raid-plan-persistence-doc" not in codes
    assert "overlapping-plan-persistence" in codes
    assert "catalog-family-transitive-aggregation" in codes
    assert "duplicate-class-definition" in codes
    assert "ui-class-monkey-patch" in codes
