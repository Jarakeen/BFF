#!/usr/bin/env python3
"""Safely rebuild data/processed/alchemy_effects.json through the V3 parser.

The historical V3 CLI writes its output even when required effect pages are
missing. This wrapper directs V3 into a candidate file first, inspects the
validation block, and promotes the candidate only when all required effects are
present. The authoritative processed file is therefore never replaced by a
known-incomplete rebuild.

This tool does not modify eso.db.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_DIR = ROOT / "data" / "raw"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "alchemy_effects.json"
DEFAULT_CANDIDATE = ROOT / "data" / "processed" / "alchemy_effects.candidate.json"
V3_IMPORTER = ROOT / "tools" / "import_uesp_alchemy_effects_v3.py"


def load_candidate(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Alchemy candidate payload is not a JSON object")
    return data


def candidate_required_failures(payload: dict[str, Any]) -> tuple[str, ...]:
    validation = payload.get("validation", {})
    if not isinstance(validation, dict):
        return ("candidate has no validation object",)
    missing = validation.get("missing_non_optional", [])
    if not isinstance(missing, list):
        return ("candidate validation missing_non_optional is malformed",)
    return tuple(str(value) for value in missing if str(value).strip())


def promote_candidate(*, candidate: Path, output: Path) -> tuple[bool, tuple[str, ...]]:
    payload = load_candidate(candidate)
    failures = candidate_required_failures(payload)
    if failures:
        return False, failures
    effects = payload.get("effects", [])
    if not isinstance(effects, list) or not effects:
        return False, ("candidate contains no Alchemy effects",)
    output.parent.mkdir(parents=True, exist_ok=True)
    candidate.replace(output)
    return True, ()


def rebuild(*, raw_dir: Path, output: Path, candidate: Path) -> int:
    candidate.parent.mkdir(parents=True, exist_ok=True)
    if candidate.exists():
        candidate.unlink()

    command = [
        sys.executable,
        str(V3_IMPORTER),
        "--raw-dir",
        str(raw_dir),
        "--output",
        str(candidate),
    ]
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        print(f"V3 parser exited with code {completed.returncode}; authoritative output unchanged.")
        return completed.returncode
    if not candidate.exists():
        print("V3 parser produced no candidate file; authoritative output unchanged.")
        return 1

    try:
        promoted, failures = promote_candidate(candidate=candidate, output=output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Candidate validation failed: {exc}")
        print("Authoritative output unchanged.")
        return 1

    if not promoted:
        print("Candidate is incomplete and was NOT promoted.")
        for failure in failures:
            print(f"  - {failure}")
        print(f"Candidate retained for inspection: {candidate}")
        print(f"Authoritative output unchanged:     {output}")
        return 1

    payload = load_candidate(output)
    print("========================================")
    print(" SAFE ALCHEMY CORPUS REBUILD COMPLETE")
    print("========================================")
    print(f"Effects:  {len(payload.get('effects', []))}")
    print(f"Output:   {output}")
    print("Database unchanged.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely rebuild the processed UESP Alchemy corpus")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    raise SystemExit(rebuild(raw_dir=args.raw_dir, output=args.output, candidate=args.candidate))
