from __future__ import annotations

"""Read-only evidence extraction from a Code's Combat Alerts addon ZIP.

The tool records compact factual evidence such as ESO ability IDs, the Lua data
path that references them, comments naming mechanics, alert table membership,
and explicit boss-health gates. It never writes source JSON or eso.db and does
not copy addon source code into the repository.
"""

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import zipfile


MANIFEST_PATH = "CombatAlerts/CombatAlerts.addon"
MODULE_PREFIX = "CombatAlerts/modules/"


@dataclass(frozen=True)
class AddonMeta:
    title: str = ""
    version: str = ""
    addon_version: str = ""
    api_version: str = ""


@dataclass(frozen=True)
class Evidence:
    module: str
    zone_id: int | None
    zone_name: str
    evidence_type: str
    data_path: str
    ability_id: int
    source_name: str
    source_comment: str
    condition: str = ""


def _decode(zf: zipfile.ZipFile, member: str) -> str:
    return zf.read(member).decode("utf-8", errors="replace")


def _manifest_meta(text: str) -> AddonMeta:
    def field(name: str) -> str:
        match = re.search(rf"(?m)^##\s*{re.escape(name)}:\s*(.*?)\s*$", text)
        return match.group(1).strip() if match else ""

    return AddonMeta(
        title=field("Title"),
        version=field("Version"),
        addon_version=field("AddOnVersion"),
        api_version=field("APIVersion"),
    )


def _module_zone(text: str) -> tuple[int | None, str]:
    match = re.search(r"Module\.ZONES\s*=\s*\{\s*(\d+)\s*,?\s*--\s*([^\r\n]+)", text, re.S)
    if not match:
        return None, ""
    return int(match.group(1)), match.group(2).strip()


def _comment_name(comment: str) -> str:
    text = comment.strip()
    # Preserve the source comment verbatim elsewhere; this is just a compact
    # display name with trailing parenthetical implementation notes removed.
    return re.sub(r"\s*\([^)]*\)\s*$", "", text).strip()


def _extract_table_evidence(text: str, module: str, zone_id: int | None, zone_name: str) -> list[Evidence]:
    evidence: list[Evidence] = []
    stack: list[str] = []
    in_data = False
    in_alert_table = ""
    brace_depth = 0

    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        if not in_data and re.match(r"\s*Module\.DATA\s*=\s*\{", line):
            in_data = True
            stack = ["DATA"]
            brace_depth = line.count("{") - line.count("}")
            continue

        alert_match = re.match(r"\s*self\.(TIMER_ALERTS_LEGACY|AOE_ALERTS)\s*=\s*\{", line)
        if alert_match:
            in_alert_table = alert_match.group(1)
            brace_depth = line.count("{") - line.count("}")
            continue

        if in_data:
            named_table = re.match(r"\s*([A-Za-z_]\w*)\s*=\s*\{\s*(?:--.*)?$", line)
            if named_table:
                stack.append(named_table.group(1))
                brace_depth += 1
                continue

            simple = re.match(r"\s*([A-Za-z_]\w*)\s*=\s*(\d+)\s*,?\s*(?:--\s*(.*))?$", line)
            if simple:
                key, ability, comment = simple.group(1), int(simple.group(2)), (simple.group(3) or "").strip()
                evidence.append(Evidence(
                    module=module,
                    zone_id=zone_id,
                    zone_name=zone_name,
                    evidence_type="data_constant",
                    data_path=".".join([*stack, key]),
                    ability_id=ability,
                    source_name=_comment_name(comment) or key,
                    source_comment=comment,
                ))

            indexed = re.match(r"\s*\[(\d+)\]\s*=\s*.+?\s*,?\s*(?:--\s*(.*))?$", line)
            if indexed:
                ability, comment = int(indexed.group(1)), (indexed.group(2) or "").strip()
                evidence.append(Evidence(
                    module=module,
                    zone_id=zone_id,
                    zone_name=zone_name,
                    evidence_type="data_index",
                    data_path=".".join(stack),
                    ability_id=ability,
                    source_name=_comment_name(comment),
                    source_comment=comment,
                ))

            opens = line.count("{")
            closes = line.count("}")
            brace_depth += opens - closes
            for _ in range(min(closes, max(len(stack) - 1, 0))):
                stack.pop()
            if brace_depth <= 0:
                in_data = False
                stack = []
            continue

        if in_alert_table:
            indexed = re.match(r"\s*\[(\d+)\]\s*=\s*.+?\s*,?\s*(?:--\s*(.*))?$", line)
            if indexed:
                ability, comment = int(indexed.group(1)), (indexed.group(2) or "").strip()
                evidence.append(Evidence(
                    module=module,
                    zone_id=zone_id,
                    zone_name=zone_name,
                    evidence_type=("timer_alert" if in_alert_table == "TIMER_ALERTS_LEGACY" else "aoe_alert"),
                    data_path=in_alert_table,
                    ability_id=ability,
                    source_name=_comment_name(comment),
                    source_comment=comment,
                ))
            brace_depth += line.count("{") - line.count("}")
            if brace_depth <= 0:
                in_alert_table = ""

    return evidence


def _extract_conditions(text: str, module: str, zone_id: int | None, zone_name: str) -> list[Evidence]:
    result: list[Evidence] = []

    # Concrete condition used in Rockgrove: generic unit-spawn event is only
    # treated as the Bahsei Fire Behemoth after Bahsei has been identified and
    # boss1 health is below 51%. Keep the condition as evidence, not a phase.
    if "DATA.behemothSpawn" in text:
        id_match = re.search(r"behemothSpawn\s*=\s*(\d+)", text)
        gate_match = re.search(r"GetUnitHealthPercent\(\"boss1\"\)\s*([<>]=?)\s*(\d+)", text)
        if id_match and gate_match:
            result.append(Evidence(
                module=module,
                zone_id=zone_id,
                zone_name=zone_name,
                evidence_type="health_gate",
                data_path="DATA.behemothSpawn",
                ability_id=int(id_match.group(1)),
                source_name="Fire Behemoth spawn detector",
                source_comment="generic spawn event filtered by encounter state",
                condition=f"boss1 health {gate_match.group(1)} {gate_match.group(2)}%",
            ))

    return result


def extract(zip_path: Path, modules: list[str]) -> dict:
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        if MANIFEST_PATH not in names:
            raise ValueError(f"Combat Alerts manifest not found: {MANIFEST_PATH}")
        meta = _manifest_meta(_decode(zf, MANIFEST_PATH))
        rows: list[Evidence] = []

        for module in modules:
            stem = module[:-4] if module.endswith(".lua") else module
            member = f"{MODULE_PREFIX}{stem}.lua"
            if member not in names:
                raise ValueError(f"module not found in ZIP: {member}")
            text = _decode(zf, member)
            zone_id, zone_name = _module_zone(text)
            rows.extend(_extract_table_evidence(text, stem, zone_id, zone_name))
            rows.extend(_extract_conditions(text, stem, zone_id, zone_name))

    # Deduplicate the same ability/path/type combination while retaining the
    # source wording that justified it.
    unique: dict[tuple, Evidence] = {}
    for row in rows:
        key = (row.module, row.evidence_type, row.data_path, row.ability_id, row.condition)
        unique.setdefault(key, row)

    ordered = sorted(
        unique.values(),
        key=lambda row: (row.module, row.evidence_type, row.data_path, row.ability_id),
    )
    return {
        "source_type": "combat_addon",
        "source_name": meta.title or "Code's Combat Alerts",
        "source_version": meta.version,
        "addon_version": meta.addon_version,
        "api_version": meta.api_version,
        "zip_name": zip_path.name,
        "modules": modules,
        "evidence": [asdict(row) for row in ordered],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract read-only encounter evidence from a Combat Alerts ZIP")
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--module", action="append", dest="modules", default=[])
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    modules = args.modules or ["u30", "u34"]
    try:
        report = extract(args.zip_path, modules)
    except (OSError, zipfile.BadZipFile, KeyError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print("=" * 76)
    print(" COMBAT ALERTS ENCOUNTER EVIDENCE - READ ONLY")
    print("=" * 76)
    print(f"source:       {report['source_name']} {report['source_version']}")
    print(f"addon/API:    {report['addon_version']} / {report['api_version']}")
    print(f"zip:          {report['zip_name']}")
    print(f"modules:      {', '.join(report['modules'])}")
    print(f"evidence rows:{len(report['evidence']):8}")
    print()

    by_module: dict[str, list[dict]] = {}
    for row in report["evidence"]:
        by_module.setdefault(row["module"], []).append(row)

    for module, rows in by_module.items():
        zone = rows[0].get("zone_name") or "unknown zone"
        zone_id = rows[0].get("zone_id")
        print(f"--- {module}: {zone} [{zone_id or 'unknown'}] ---")
        for row in rows:
            name = row.get("source_name") or "(unnamed)"
            condition = f" | {row['condition']}" if row.get("condition") else ""
            print(
                f"  {row['ability_id']:6} | {row['evidence_type']:<13} | "
                f"{row['data_path']:<28} | {name}{condition}"
            )
        print()

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Report written: {args.json_output}")

    print("No addon files, source JSON files, or database rows were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
