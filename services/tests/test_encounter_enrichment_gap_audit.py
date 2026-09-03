from pathlib import Path

from tools.audit_encounter_enrichment_gaps import CANONICAL_SOURCE_ROOT, build_parser


def test_enrichment_gap_audit_defaults_to_canonical_source_root() -> None:
    args = build_parser().parse_args([])

    assert Path(args.source_root) == CANONICAL_SOURCE_ROOT
    assert CANONICAL_SOURCE_ROOT == Path("data/eso_info")


def test_enrichment_gap_audit_accepts_source_root_override() -> None:
    args = build_parser().parse_args(["--source-root", "tmp/encounters"])

    assert args.source_root == "tmp/encounters"


def test_enrichment_gap_audit_preserves_legacy_uesp_root_alias() -> None:
    args = build_parser().parse_args(["--uesp-root", "legacy/uesp"])

    assert args.source_root == "legacy/uesp"
