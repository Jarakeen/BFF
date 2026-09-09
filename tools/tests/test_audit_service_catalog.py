from __future__ import annotations

from pathlib import Path

from services.service_catalog import (
    ServiceAuthority,
    ServiceDescriptor,
)
from tools.audit_service_catalog import audit_service_catalog


def _write_module(root: Path, module: str, content: str = "class ExampleService: pass\n") -> None:
    path = root.joinpath(*module.split(".")).with_suffix(".py")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _descriptor(
    service_id: str,
    *,
    implementation_path: str,
    dependencies: tuple[str, ...] = (),
    responsibility: str = "thing",
    authority: ServiceAuthority = ServiceAuthority.CANONICAL,
    superseded_by: str | None = None,
) -> ServiceDescriptor:
    return ServiceDescriptor(
        service_id=service_id,
        domain="test",
        purpose="test service",
        implementation_path=implementation_path,
        dependencies=dependencies,
        responsibilities=(responsibility,),
        authority=authority,
        superseded_by=superseded_by,
    )


def test_audit_accepts_valid_registered_dependency_graph(tmp_path: Path) -> None:
    _write_module(tmp_path, "services.alpha_service")
    _write_module(tmp_path, "services.beta_service")
    descriptors = (
        _descriptor("alpha", implementation_path="services.alpha_service"),
        _descriptor(
            "beta",
            implementation_path="services.beta_service",
            dependencies=("alpha",),
            responsibility="other",
        ),
    )

    result = audit_service_catalog(root=tmp_path, descriptors=descriptors)

    assert result.errors == ()


def test_audit_reports_duplicate_ids_broken_paths_and_missing_dependencies(
    tmp_path: Path,
) -> None:
    _write_module(tmp_path, "services.alpha_service")
    descriptors = (
        _descriptor("alpha", implementation_path="services.alpha_service"),
        _descriptor(
            "alpha",
            implementation_path="services.missing_service",
            dependencies=("ghost",),
            responsibility="other",
        ),
    )

    result = audit_service_catalog(root=tmp_path, descriptors=descriptors)
    codes = {row.code for row in result.errors}

    assert "duplicate-service-id" in codes
    assert "broken-implementation-path" in codes
    assert "missing-dependency" in codes


def test_audit_reports_dependency_cycle(tmp_path: Path) -> None:
    _write_module(tmp_path, "services.alpha_service")
    _write_module(tmp_path, "services.beta_service")
    descriptors = (
        _descriptor(
            "alpha",
            implementation_path="services.alpha_service",
            dependencies=("beta",),
        ),
        _descriptor(
            "beta",
            implementation_path="services.beta_service",
            dependencies=("alpha",),
            responsibility="other",
        ),
    )

    result = audit_service_catalog(root=tmp_path, descriptors=descriptors)

    assert "circular-dependency" in {row.code for row in result.errors}


def test_audit_reports_unregistered_service_module_as_warning(tmp_path: Path) -> None:
    _write_module(tmp_path, "services.registered_service")
    _write_module(tmp_path, "services.forgotten_service")
    descriptors = (
        _descriptor("registered", implementation_path="services.registered_service"),
    )

    result = audit_service_catalog(root=tmp_path, descriptors=descriptors)

    assert any(
        row.code == "unregistered-service-module"
        and row.message == "services/forgotten_service.py"
        for row in result.warnings
    )


def test_audit_ignores_catalog_infrastructure_module(tmp_path: Path) -> None:
    _write_module(
        tmp_path,
        "services.service_catalog",
        "class ServiceCatalog: pass\n",
    )

    result = audit_service_catalog(root=tmp_path, descriptors=())

    assert not any(
        row.code == "unregistered-service-module"
        and row.message == "services/service_catalog.py"
        for row in result.warnings
    )


def test_audit_ignores_verified_old_page_only_service_utilities(tmp_path: Path) -> None:
    _write_module(tmp_path, "services.ai_service", "class AIService: pass\n")
    _write_module(tmp_path, "services.json_service", "class JsonService: pass\n")
    _write_module(tmp_path, "services.validation_service", "class ValidationService: pass\n")
    _write_module(tmp_path, "services.still_current_service")

    result = audit_service_catalog(root=tmp_path, descriptors=())
    warning_paths = {
        row.message
        for row in result.warnings
        if row.code == "unregistered-service-module"
    }

    assert "services/ai_service.py" not in warning_paths
    assert "services/json_service.py" not in warning_paths
    assert "services/validation_service.py" not in warning_paths
    assert "services/still_current_service.py" in warning_paths


def test_audit_reports_deprecated_service_without_successor(tmp_path: Path) -> None:
    _write_module(tmp_path, "services.old_service")
    descriptors = (
        _descriptor(
            "old",
            implementation_path="services.old_service",
            authority=ServiceAuthority.DEPRECATED,
        ),
    )

    result = audit_service_catalog(root=tmp_path, descriptors=descriptors)

    assert "deprecated-without-successor" in {row.code for row in result.warnings}
