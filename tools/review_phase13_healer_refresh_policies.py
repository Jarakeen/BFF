from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _parse_identity(value: str) -> tuple[str, int]:
    text = str(value or "").strip()
    if ":" not in text:
        raise argparse.ArgumentTypeError("expected 'Skill Name:coefficient_number'")
    name, raw_coefficient = text.rsplit(":", 1)
    name = name.strip()
    try:
        coefficient = int(raw_coefficient)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("coefficient_number must be an integer") from exc
    if not name or coefficient <= 0:
        raise argparse.ArgumentTypeError("skill name and positive coefficient_number are required")
    return name, coefficient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Write a separate explicitly reviewed healer periodic refresh-policy fixture. "
            "This command does not infer policies from candidate audits."
        )
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--approve-restart", type=_parse_identity, action="append", default=[])
    parser.add_argument("--game-version", default="U50")
    parser.add_argument("--review-note", required=True)
    parser.add_argument("--evidence-source", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    note = str(args.review_note or "").strip()
    game_version = str(args.game_version or "").strip()
    if not note:
        raise ValueError("--review-note must be non-empty")
    if not game_version:
        raise ValueError("--game-version must be non-empty")
    if not args.approve_restart:
        raise ValueError("at least one --approve-restart entry is required")

    evidence_sources = tuple(
        str(value).strip() for value in args.evidence_source if str(value).strip()
    )
    seen: set[tuple[str, int]] = set()
    policies = []
    for source_name, coefficient_number in args.approve_restart:
        key = (source_name.casefold(), int(coefficient_number))
        if key in seen:
            raise ValueError(
                f"duplicate refresh policy approval for {source_name} coefficient {coefficient_number}"
            )
        seen.add(key)
        provenance = [note]
        provenance.extend(evidence_sources)
        policies.append(
            {
                "source_name": source_name,
                "coefficient_number": int(coefficient_number),
                "game_version": game_version,
                "refresh_policy": "restart",
                "provenance": provenance,
            }
        )

    payload = {
        "schema_version": 1,
        "review_status": "reviewed",
        "game_version": game_version,
        "policies": policies,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print("PHASE 13 HEALER REFRESH POLICY REVIEW")
    print(f"Reviewed: {args.output}")
    print("Approved RESTART policies:")
    for source_name, coefficient_number in args.approve_restart:
        print(f"  - {source_name} coefficient {coefficient_number} [{game_version}]")
    print("Boundary: separate reviewed fixture; no candidate audit source was modified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
