from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "services" / "build_service.py"


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")

    if "from services.canonical_build_bridge import CanonicalBuildBridge" in text:
        print("Canonical build bridge is already wired.")
        return

    text = text.replace(
        "from models.build_model import BuildRoster, PlayerBuild\n",
        "from models.build_model import BuildRoster, PlayerBuild\nfrom services.canonical_build_bridge import CanonicalBuildBridge\n",
        1,
    )

    init_pattern = re.compile(
        r"    def __init__\(self, builds_path: Path\):\n\n"
        r"        self\.builds_path = Path\(builds_path\)\n",
        re.MULTILINE,
    )
    text, init_count = init_pattern.subn(
        "    def __init__(self, builds_path: Path):\n\n"
        "        self.builds_path = Path(builds_path)\n"
        "        self.canonical = CanonicalBuildBridge(self.builds_path)\n",
        text,
        count=1,
    )
    if init_count != 1:
        raise SystemExit("Could not find the expected BuildService.__init__ block; no changes made.")

    persistence_pattern = re.compile(
        r"    def load\(self\) -> BuildRoster:\n.*?"
        r"    # --------------------------------------------------\n"
        r"    # CSV export\n",
        re.DOTALL,
    )
    replacement = (
        "    def load(self) -> BuildRoster:\n\n"
        "        return self.canonical.load()\n\n"
        "    def save(self, roster: BuildRoster) -> None:\n\n"
        "        self.canonical.save(roster)\n\n"
        "    # --------------------------------------------------\n"
        "    # CSV export\n"
    )
    text, persistence_count = persistence_pattern.subn(
        replacement, text, count=1
    )
    if persistence_count != 1:
        raise SystemExit("Could not find the expected BuildService persistence block; no changes made.")

    TARGET.write_text(text, encoding="utf-8")
    print(f"Canonical build bridge wired into {TARGET}")
    print("builds.json remains a compatibility mirror; characters.json is now the canonical source.")


if __name__ == "__main__":
    main()
