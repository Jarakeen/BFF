from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PARSER = REPO_ROOT / "services" / "uesp" / "uesp_parser.py"

OLD_IMPORT = "from services.uesp.uesp_client import UespPage\n"
NEW_IMPORT = OLD_IMPORT + "from services.uesp.phase_extractor import extract_phases\n"
OLD_CALL = "        phases = _extract_phases(parsed.all_blocks)"
NEW_CALL = "        phases = extract_phases(parsed.all_blocks)"


def main() -> None:
    text = PARSER.read_text(encoding="utf-8")

    if "from services.uesp.phase_extractor import extract_phases" in text:
        print("PHASE EXTRACTOR ALREADY WIRED")
        return

    if OLD_IMPORT not in text:
        raise SystemExit("Could not find the expected UESP client import; parser may have changed.")
    if OLD_CALL not in text:
        raise SystemExit("Could not find the expected phase extraction call; parser may have changed.")

    updated = text.replace(OLD_IMPORT, NEW_IMPORT, 1).replace(OLD_CALL, NEW_CALL, 1)
    PARSER.write_text(updated, encoding="utf-8")

    print("PHASE EXTRACTOR WIRED")
    print(f"  parser: {PARSER}")
    print("  next:   python -m tools.test_uesp_xalvakka")


if __name__ == "__main__":
    main()
