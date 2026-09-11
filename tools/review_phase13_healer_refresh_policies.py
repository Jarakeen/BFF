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
    parser.add_argument(
        "--preserve-existing",
        action="store_true",
        help=(
            "preserve already-reviewed policies from --output before appending new explicit approvals; "
            "fails closed on malformed, conflicting, or cross-version existing evidence"
        ),
    )
    return parser


def _load_existing_policies(path: Path, *, game_version: str) -> list[dict]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("existing refresh-policy fixture must be a JSON object")
    if payload.get("review_status") != "reviewed":
        raise ValueError("existing refresh-policy fixture is not explicitly reviewed")
    existing_version = str(payload.get("game_version") or "").strip()
    if existing_version != game_version:
        raise ValueError(
            f"existing refresh-policy fixture game_version {existing_version!r} does not match {game_version!r}"
        )
    raw_policies = payload.get("policies")
    if not isinstance(raw_policies, list):
        raise ValueError("existing refresh-policy fixture policies must be a list")

    policies: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for index, raw in enumerate(raw_policies, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"existing refresh policy {index} must be an object")
        source_name = str(raw.get("source_name") or "").strip()
        try:
            coefficient_number = int(raw.get("coefficient_number"))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"existing refresh policy {index} has invalid coefficient_number"
            ) from exc
        policy_version = str(raw.get("game_version") or existing_version).strip()
        refresh_policy = str(raw.get("refresh_policy") or "").strip().casefold()
        provenance = raw.get("provenance")
        if not source_name or coefficient_number <= 0:
            raise ValueError(f"existing refresh policy {index} has invalid identity")
        if policy_version != game_version:
            raise ValueError(
                f"existing refresh policy {source_name} coefficient {coefficient_number} has mismatched game_version"
            )
        if refresh_policy != "restart":
            raise ValueError(
                f"existing refresh policy {source_name} coefficient {coefficient_number} is unsupported: {refresh_policy!r}"
            )
        if not isinstance(provenance, list) or not all(
            isinstance(value, str) and value.strip() for value in provenance
        ):
            raise ValueError(
                f"existing refresh policy {source_name} coefficient {coefficient_number} has invalid provenance"
            )
        key = (source_name.casefold(), coefficient_number)
        if key in seen:
            raise ValueError(
                f"duplicate existing refresh policy for {source_name} coefficient {coefficient_number}"
            )
        seen.add(key)
        policies.append(
            {
                "source_name": source_name,
                "coefficient_number": coefficient_number,
                "game_version": game_version,
                "refresh_policy": "restart",
                "provenance": [str(value).strip() for value in provenance],
            }
        )
    return policies


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
    policies = (
        _load_existing_policies(args.output, game_version=game_version)
        if args.preserve_existing
        else []
    )
    seen: set[tuple[str, int]] = {
        (str(item["source_name"]).casefold(), int(item["coefficient_number"]))
        for item in policies
    }
    preserved_count = len(policies)

    for source_name, coefficient_number in args.approve_restart:
        key = (source_name.casefold(), int(coefficient_number))
        if key in seen:
            raise ValueError(
                f"refresh policy already exists for {source_name} coefficient {coefficient_number}; "
                "existing reviewed evidence is preserved and must not be silently replaced"
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
    if args.preserve_existing:
        print(f"Preserved existing reviewed policies: {preserved_count}")
    print("Approved RESTART policies:")
    for source_name, coefficient_number in args.approve_restart:
        print(f"  - {source_name} coefficient {coefficient_number} [{game_version}]")
    print("Boundary: separate reviewed fixture; no candidate audit source was modified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
