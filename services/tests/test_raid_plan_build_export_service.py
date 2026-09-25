from __future__ import annotations

from types import SimpleNamespace

from openpyxl import load_workbook
from pypdf import PdfReader

from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan, RaidPlanMember
from services.raid_plan_build_export_service import (
    export_raid_plan_builds_pdf,
    export_raid_plan_builds_xlsx,
    raid_plan_build_export,
    raid_plan_discord_builds_text,
)


def test_linked_build_exports_include_saved_bars_planned_skills_and_unresolved_seats(tmp_path) -> None:
    build = PlayerBuild(
        BuildId="build-1",
        Gamertag="A&B <Raid>",
        Name="Healer & Friend",
        BuildName="=SUM(1,2)",
        EsoClass="Templar",
        Role="Healer",
        FrontBarSkills=["Combat Prayer", "", "", "", "", ""],
        BackBarSkills=["Energy Orb", "", "", "", "", ""],
    )
    build.Armor["Head"]["Set"] = "Ozezan the Inferno"
    plan = RaidPlan(
        plan_id="plan-1",
        trial_id="vDSR",
        name="Friends & Family <Friday>",
        difficulty="Veteran",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                selected_build_id="build-1",
                planned_skills=("Aggressive Horn",),
                primary_assignment="Main healer",
            ),
            RaidPlanMember(seat_id="tank-1", selected_build_id="missing"),
        ),
    )
    service = SimpleNamespace(load=lambda: SimpleNamespace(Members=[build]))
    export = raid_plan_build_export(plan, service)

    assert len(export.seats) == 1
    assert export.unresolved_seats == ("tank-1",)
    assert "**healer-1**" in raid_plan_discord_builds_text(plan, export)

    xlsx = export_raid_plan_builds_xlsx(plan, export, tmp_path / "builds.xlsx")
    workbook = load_workbook(xlsx)
    sheet = workbook["Raid Builds"]
    assert sheet["A1"].value == plan.name
    assert sheet["F5"].value == "=SUM(1,2)"
    assert sheet["F5"].data_type == "s"
    assert sheet["H5"].value == "Combat Prayer"
    assert sheet["I5"].value == "Energy Orb"
    assert sheet["J5"].value == "Aggressive Horn"
    assert "Ozezan the Inferno" in sheet["G5"].value
    assert sheet.freeze_panes == "D5"
    assert sheet.sheet_view.showGridLines is False
    assert workbook["Unresolved"]["A2"].value == "tank-1"
    workbook.close()

    pdf = export_raid_plan_builds_pdf(plan, export, tmp_path / "builds.pdf")
    extracted = "\n".join(page.extract_text() for page in PdfReader(pdf).pages)
    assert "Friends & Family <Friday>" in extracted
    assert "Combat Prayer" in extracted
    assert "Energy Orb" in extracted
    assert "Aggressive Horn" in extracted
    assert "tank-1" in extracted
