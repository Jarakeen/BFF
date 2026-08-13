# services/build_service.py
#
# Persistence and export for the Builds page.
#
# Builds are stored as their own JSON file (data/builds.json)
# rather than in eso.db -- eso.db is reference data shipped
# with the Foundry (sets, skills, races...); builds are the
# user's own roster data, same treatment as
# CurrentExpedition.json / roster.

from __future__ import annotations

import csv
import json
from pathlib import Path

from models.build_model import BuildRoster, PlayerBuild


class BuildService:

    def __init__(self, builds_path: Path):

        self.builds_path = Path(builds_path)

    # --------------------------------------------------
    # Persistence
    # --------------------------------------------------

    def load(self) -> BuildRoster:

        if not self.builds_path.exists():
            return BuildRoster()

        try:

            data = json.loads(
                self.builds_path.read_text(encoding="utf-8")
            )

        except (OSError, json.JSONDecodeError):
            return BuildRoster()

        return BuildRoster.from_dict(data)

    def save(self, roster: BuildRoster) -> None:

        self.builds_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.builds_path.write_text(
            json.dumps(roster.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # --------------------------------------------------
    # CSV export
    # --------------------------------------------------

    CSV_COLUMNS = [
        "Name",
        "Gamertag",
        "Race",
        "Class",
        "Head",
        "Shoulders",
        "Chest",
        "Hands",
        "Waist",
        "Legs",
        "Feet",
        "Front Bar Weapon",
        "Back Bar Weapon",
        "Necklace",
        "Ring 1",
        "Ring 2",
        "Champion Points",
        "Front Bar Skills",
        "Back Bar Skills",
        "Food",
        "Potion",
        "Boss",
        "Boss Front Bar Skills",
        "Boss Back Bar Skills",
        "Boss Food",
        "Boss Potion",
        "Boss Notes",
        "Notes",
    ]

    def export_csv(self, roster: BuildRoster, path: Path) -> None:
        """
        One row per member for the default loadout, plus one
        additional row per boss alternate loadout, so every
        alternate is visible without collapsing the sheet
        into a single wall of columns.
        """

        path = Path(path)

        with path.open("w", newline="", encoding="utf-8") as handle:

            writer = csv.writer(handle)

            writer.writerow(self.CSV_COLUMNS)

            for member in roster.Members:

                if not member.Name and not member.Gamertag:
                    continue

                writer.writerow(self._base_row(member))

                for boss in member.BossLoadouts:

                    if not boss.BossName:
                        continue

                    writer.writerow(
                        self._base_row(member)[:17]
                        + [
                            self._bar_text(member.FrontBarSkills),
                            self._bar_text(member.BackBarSkills),
                            member.Food,
                            member.Potion,
                            boss.BossName,
                            self._bar_text(boss.FrontBarSkills),
                            self._bar_text(boss.BackBarSkills),
                            boss.Food,
                            boss.Potion,
                            boss.Notes,
                            member.Notes,
                        ]
                    )

    def _base_row(self, member: PlayerBuild) -> list[str]:

        armor = [
            member.Armor.get(slot, {}).get("Set", "")
            for slot in (
                "Head", "Shoulders", "Chest", "Hands",
                "Waist", "Legs", "Feet",
            )
        ]

        cp = "; ".join(
            f"{c.Name} ({c.Points})" if c.Points else c.Name
            for c in member.ChampionPoints
            if c.Name
        )

        return [
            member.Name,
            member.Gamertag,
            member.Race,
            member.EsoClass,
            *armor,
            member.FrontBarWeapon.Set,
            member.BackBarWeapon.Set,
            member.Necklace.Set,
            member.Ring1.Set,
            member.Ring2.Set,
            cp,
            self._bar_text(member.FrontBarSkills),
            self._bar_text(member.BackBarSkills),
            member.Food,
            member.Potion,
            "",
            "",
            "",
            "",
            "",
            "",
            member.Notes,
        ]

    @staticmethod
    def _bar_text(skills: list[str]) -> str:

        return " / ".join(s for s in skills if s)

    # --------------------------------------------------
    # PDF export
    # --------------------------------------------------

    def export_pdf(self, roster: BuildRoster, path: Path) -> None:
        """
        One section per member. Uses reportlab if it's
        installed; otherwise falls back to a plain-text
        PDF built with the stdlib so export still works on
        a machine that hasn't `pip install reportlab`-ed.
        """

        path = Path(path)

        try:
            self._export_pdf_reportlab(roster, path)
        except ImportError:
            self._export_pdf_fallback(roster, path)

    def _export_pdf_reportlab(self, roster: BuildRoster, path: Path) -> None:

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            PageBreak,
        )

        styles = getSampleStyleSheet()

        doc = SimpleDocTemplate(
            str(path),
            pagesize=LETTER,
            topMargin=0.6 * inch,
            bottomMargin=0.6 * inch,
        )

        story = []

        members = [
            m for m in roster.Members
            if m.Name or m.Gamertag
        ]

        for index, member in enumerate(members):

            story.append(
                Paragraph(
                    member.Name or "Unnamed Member",
                    styles["Title"],
                )
            )

            if member.Gamertag:

                story.append(
                    Paragraph(
                        f"@{member.Gamertag}",
                        styles["Normal"],
                    )
                )

            story.append(Spacer(1, 8))

            story.append(
                Paragraph(
                    f"Race: {member.Race or '-'} &nbsp;&nbsp; "
                    f"Class: {member.EsoClass or '-'}",
                    styles["Normal"],
                )
            )

            story.append(Spacer(1, 10))

            armor_rows = [["Slot", "Set", "Trait"]]

            for slot in (
                "Head", "Shoulders", "Chest", "Hands",
                "Waist", "Legs", "Feet",
            ):
                entry = member.Armor.get(slot, {})
                armor_rows.append(
                    [slot, entry.get("Set", ""), entry.get("Trait", "")]
                )

            armor_rows.append(
                ["Front Bar Weapon", member.FrontBarWeapon.Set, member.FrontBarWeapon.Trait]
            )
            armor_rows.append(
                ["Back Bar Weapon", member.BackBarWeapon.Set, member.BackBarWeapon.Trait]
            )
            armor_rows.append(
                ["Necklace", member.Necklace.Set, member.Necklace.Trait]
            )
            armor_rows.append(
                ["Ring 1", member.Ring1.Set, member.Ring1.Trait]
            )
            armor_rows.append(
                ["Ring 2", member.Ring2.Set, member.Ring2.Trait]
            )

            table = Table(armor_rows, colWidths=[1.6 * inch, 2.6 * inch, 1.6 * inch])

            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b2f36")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                    ]
                )
            )

            story.append(table)

            story.append(Spacer(1, 10))

            story.append(
                Paragraph(
                    f"<b>Champion Points:</b> "
                    + (
                        "; ".join(
                            f"{c.Name} ({c.Points})" if c.Points else c.Name
                            for c in member.ChampionPoints
                            if c.Name
                        )
                        or "-"
                    ),
                    styles["Normal"],
                )
            )

            story.append(Spacer(1, 6))

            story.append(
                Paragraph(
                    f"<b>Front Bar:</b> {self._bar_text(member.FrontBarSkills) or '-'}",
                    styles["Normal"],
                )
            )

            story.append(
                Paragraph(
                    f"<b>Back Bar:</b> {self._bar_text(member.BackBarSkills) or '-'}",
                    styles["Normal"],
                )
            )

            story.append(Spacer(1, 6))

            story.append(
                Paragraph(
                    f"<b>Food:</b> {member.Food or '-'} &nbsp;&nbsp; "
                    f"<b>Potion:</b> {member.Potion or '-'}",
                    styles["Normal"],
                )
            )

            if member.Notes:

                story.append(Spacer(1, 6))

                story.append(
                    Paragraph(f"<b>Notes:</b> {member.Notes}", styles["Normal"])
                )

            if member.BossLoadouts:

                story.append(Spacer(1, 12))

                story.append(
                    Paragraph("Boss Alternates", styles["Heading2"])
                )

                for boss in member.BossLoadouts:

                    if not boss.BossName:
                        continue

                    story.append(
                        Paragraph(f"<b>{boss.BossName}</b>", styles["Heading3"])
                    )

                    if any(boss.FrontBarSkills):
                        story.append(
                            Paragraph(
                                f"Front Bar: {self._bar_text(boss.FrontBarSkills)}",
                                styles["Normal"],
                            )
                        )

                    if any(boss.BackBarSkills):
                        story.append(
                            Paragraph(
                                f"Back Bar: {self._bar_text(boss.BackBarSkills)}",
                                styles["Normal"],
                            )
                        )

                    if boss.Food or boss.Potion:
                        story.append(
                            Paragraph(
                                f"Food: {boss.Food or '-'} &nbsp;&nbsp; "
                                f"Potion: {boss.Potion or '-'}",
                                styles["Normal"],
                            )
                        )

                    if boss.Notes:
                        story.append(
                            Paragraph(f"Notes: {boss.Notes}", styles["Normal"])
                        )

                    story.append(Spacer(1, 6))

            if index < len(members) - 1:
                story.append(PageBreak())

        doc.build(story)

    def _export_pdf_fallback(self, roster: BuildRoster, path: Path) -> None:
        """
        Minimal single-page-per-member PDF with no external
        dependency, for a machine without reportlab. Plain
        monospace text, no tables/styling.
        """

        lines_per_member: list[list[str]] = []

        for member in roster.Members:

            if not member.Name and not member.Gamertag:
                continue

            lines = [
                member.Name or "Unnamed Member",
                f"@{member.Gamertag}" if member.Gamertag else "",
                f"Race: {member.Race or '-'}    Class: {member.EsoClass or '-'}",
                "",
                "Armor:",
            ]

            for slot in (
                "Head", "Shoulders", "Chest", "Hands",
                "Waist", "Legs", "Feet",
            ):
                entry = member.Armor.get(slot, {})
                lines.append(
                    f"  {slot}: {entry.get('Set', '') or '-'} "
                    f"({entry.get('Trait', '') or '-'})"
                )

            lines.append(f"  Front Bar Weapon: {member.FrontBarWeapon.Set or '-'}")
            lines.append(f"  Back Bar Weapon: {member.BackBarWeapon.Set or '-'}")
            lines.append(f"  Necklace: {member.Necklace.Set or '-'}")
            lines.append(f"  Ring 1: {member.Ring1.Set or '-'}")
            lines.append(f"  Ring 2: {member.Ring2.Set or '-'}")
            lines.append("")
            lines.append(f"Front Bar Skills: {self._bar_text(member.FrontBarSkills) or '-'}")
            lines.append(f"Back Bar Skills: {self._bar_text(member.BackBarSkills) or '-'}")
            lines.append(f"Food: {member.Food or '-'}    Potion: {member.Potion or '-'}")

            if member.Notes:
                lines.append(f"Notes: {member.Notes}")

            for boss in member.BossLoadouts:

                if not boss.BossName:
                    continue

                lines.append("")
                lines.append(f"-- Boss Alternate: {boss.BossName} --")
                lines.append(f"  Front Bar: {self._bar_text(boss.FrontBarSkills) or '-'}")
                lines.append(f"  Back Bar: {self._bar_text(boss.BackBarSkills) or '-'}")

                if boss.Food or boss.Potion:
                    lines.append(f"  Food: {boss.Food or '-'}   Potion: {boss.Potion or '-'}")

                if boss.Notes:
                    lines.append(f"  Notes: {boss.Notes}")

            lines_per_member.append(lines)

        self._write_plaintext_pdf(lines_per_member, path)

    @staticmethod
    def _write_plaintext_pdf(pages: list[list[str]], path: Path) -> None:
        """
        Hand-rolled single-column text PDF (Helvetica,
        one page per member) using only the PDF primitives
        needed for left-aligned monospace-ish text -- no
        external dependency.
        """

        def escape(text: str) -> str:
            return (
                text.replace("\\", r"\\")
                .replace("(", r"\(")
                .replace(")", r"\)")
            )

        objects: list[bytes] = []

        font_obj_num = 2

        page_obj_nums = []
        content_obj_nums = []

        # Reserve numbers: 1 = Catalog, 2 = Font, then per
        # page a Page object + a Contents object.
        next_num = 3

        for _ in pages or [["No members yet."]]:
            page_obj_nums.append(next_num)
            next_num += 1
            content_obj_nums.append(next_num)
            next_num += 1

        pages_obj_num = next_num
        next_num += 1

        body_parts = []

        body_parts.append(
            (1, f"<< /Type /Catalog /Pages {pages_obj_num} 0 R >>".encode("latin-1"))
        )

        body_parts.append(
            (
                font_obj_num,
                b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
            )
        )

        page_refs = " ".join(f"{n} 0 R" for n in page_obj_nums)

        body_parts.append(
            (
                pages_obj_num,
                (
                    f"<< /Type /Pages /Kids [{page_refs}] "
                    f"/Count {len(page_obj_nums)} >>"
                ).encode("latin-1"),
            )
        )

        for lines, page_num, content_num in zip(
            pages or [["No members yet."]], page_obj_nums, content_obj_nums
        ):

            y = 740

            stream_lines = ["BT", "/F1 10 Tf", "12 TL", f"50 {y} Td"]

            for line in lines:

                stream_lines.append(
                    f"({escape(line)}) Tj"
                )

                stream_lines.append("0 -14 Td")

            stream_lines.append("ET")

            stream = "\n".join(stream_lines).encode("latin-1", errors="replace")

            body_parts.append(
                (
                    page_num,
                    (
                        f"<< /Type /Page /Parent {pages_obj_num} 0 R "
                        f"/Resources << /Font << /F1 {font_obj_num} 0 R >> >> "
                        f"/MediaBox [0 0 612 792] /Contents {content_num} 0 R >>"
                    ).encode("latin-1"),
                )
            )

            body_parts.append(
                (
                    content_num,
                    f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
                    + stream
                    + b"\nendstream",
                )
            )

        body_parts.sort(key=lambda item: item[0])

        buffer = bytearray()

        buffer += b"%PDF-1.4\n"

        offsets = {}

        for num, content in body_parts:

            offsets[num] = len(buffer)

            buffer += f"{num} 0 obj\n".encode("latin-1")
            buffer += content
            buffer += b"\nendobj\n"

        xref_start = len(buffer)

        total_objects = max(offsets.keys()) + 1

        buffer += f"xref\n0 {total_objects}\n".encode("latin-1")

        buffer += b"0000000000 65535 f \n"

        for num in range(1, total_objects):

            offset = offsets.get(num, 0)

            buffer += f"{offset:010d} 00000 n \n".encode("latin-1")

        buffer += (
            f"trailer\n<< /Size {total_objects} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF"
        ).encode("latin-1")

        Path(path).write_bytes(bytes(buffer))
