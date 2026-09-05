from __future__ import annotations

from services.comp_builder_build_candidates import CompBuildCandidate
from services.esologs_client import EsoLogsApiError
from services.team_role_autofill import normalize_team_role


_INSTALLED = False


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _role_matches(player_role: object, chair_role: object) -> bool:
    return (
        normalize_team_role(player_role) is not None
        and normalize_team_role(player_role) == normalize_team_role(chair_role)
    )


def _class_matches(player_class: object, chair_class: object) -> bool:
    requested = _clean(chair_class)
    if not requested or requested.casefold() == "any class":
        return True
    return _clean(player_class).casefold() == requested.casefold()


def _snapshot_candidates(page, row: int) -> tuple[CompBuildCandidate, ...]:
    if row < 0:
        return ()

    role = page._cell_text(row, 1)
    preferred_class = page._selected_class(row) or "Any class"
    rows: list[CompBuildCandidate] = []
    seen: set[str] = set()

    for result in getattr(page, "_esologs_top_team_results", ()):
        report_code = _clean(getattr(result, "ReportCode", ""))
        fight_id = int(getattr(result, "FightId", 0) or 0)
        encounter = _clean(getattr(result, "EncounterName", "")) or "Observed encounter"
        for player in getattr(result, "Players", ()):
            player_role = _clean(getattr(player, "Role", ""))
            eso_class = _clean(getattr(player, "ClassName", ""))
            if not _role_matches(player_role, role):
                continue
            if not _class_matches(eso_class, preferred_class):
                continue

            player_name = _clean(getattr(player, "Name", "")) or "Observed player"
            candidate_id = (
                f"esologs:{report_code}:{fight_id}:"
                f"{player_name.casefold()}:{player_role.casefold()}:{eso_class.casefold()}"
            )
            if candidate_id in seen:
                continue
            seen.add(candidate_id)

            gear_sets = tuple(
                _clean(value)
                for value in getattr(player, "GearSets", ())
                if _clean(value)
            )
            skills = tuple(
                _clean(value)
                for value in getattr(player, "Abilities", ())
                if _clean(value)
            )
            role_label = {
                "tank": "Tank",
                "healer": "Healer",
                "dd": "DD",
            }.get(normalize_team_role(player_role) or "", player_role or "Role")
            score = 70.0
            reasons = ["current ESO Logs ranked-team snapshot"]
            if preferred_class.casefold() != "any class":
                score += 20.0
                reasons.append(f"matches requested class {preferred_class}")
            if gear_sets:
                score += min(10.0, 2.0 * len(gear_sets))
                reasons.append("contains observed gear-set evidence")
            if skills:
                score += min(10.0, float(len(skills)))
                reasons.append("contains observed ability evidence")

            rows.append(
                CompBuildCandidate(
                    candidate_id=candidate_id,
                    name=f"{eso_class} {role_label} • {encounter} • {player_name}",
                    source_kind="esologs_snapshot",
                    source_name="ESO Logs",
                    source_url=(
                        f"https://www.esologs.com/reports/{report_code}"
                        if report_code
                        else "https://www.esologs.com/"
                    ),
                    eso_class=eso_class,
                    role=role_label,
                    gear_sets=gear_sets,
                    skills=skills,
                    mundus=_clean(getattr(player, "Mundus", "")),
                    complete_build=False,
                    unresolved=(
                        "Observed ESO Logs snapshot only; race, attributes, exact gear slots, traits, enchants, champion points, food, potions, and skill bar placement may be unresolved.",
                    ),
                    score=score,
                    score_reasons=tuple(reasons),
                )
            )

    return tuple(
        sorted(
            rows,
            key=lambda item: (-item.score, item.name.casefold(), item.candidate_id.casefold()),
        )
    )


def _refresh_live_esologs_with_snapshots(page) -> None:
    from ui import comp_builder_esologs_support as support

    trial_name = support._current_trial(page)
    if trial_name == "Custom Trial":
        page._esologs_top_team_results = ()
        support._clear_esologs_evidence(page)
        page.status.info("Choose a published trial before refreshing build sources.")
        return

    page.refresh_esologs_button.setEnabled(False)
    page.status.info(f"Fetching current top-ranked {trial_name} teams from ESO Logs...")

    try:
        service = support._top_team_service()
        trials = service.list_trials()
        trial = next(
            (
                item
                for item in trials
                if str(item.get("name", "")).strip().casefold() == trial_name.casefold()
            ),
            None,
        )
        if trial is None:
            raise EsoLogsApiError(f"ESO Logs did not return the trial {trial_name!r}.")

        results = []
        failures: list[str] = []
        for encounter in trial.get("encounters") or ():
            try:
                results.append(
                    service.get_top_team(
                        zone_id=int(trial["id"]),
                        zone_name=str(trial["name"]),
                        encounter_id=int(encounter["id"]),
                        encounter_name=str(encounter["name"]),
                    )
                )
            except (EsoLogsApiError, KeyError, TypeError, ValueError) as exc:
                failures.append(f"{encounter.get('name', 'Unknown encounter')}: {exc}")

        if not results:
            detail = failures[0] if failures else "No ranked encounters returned usable team data."
            raise EsoLogsApiError(detail)

        page._esologs_top_team_results = tuple(results)
        evidence = page._esologs_evidence_service.aggregate(
            tuple(results),
            trial_name=trial_name,
        )
        page._esologs_observed_evidence = evidence
        page.esologs_evidence_label.setText(support._format_observed_evidence(evidence))
        page.apply_esologs_button.setEnabled(True)
        support._append_report_provenance(page, evidence)
        support._refresh_selected_chair(page)

        if failures:
            page.status.warning(
                f"Loaded {len(results)} ranked-team snapshot(s) for {trial_name}; "
                f"{len(failures)} encounter(s) could not be read."
            )
        else:
            page.status.success(
                f"Loaded {len(results)} live ranked-team snapshot(s) for {trial_name}."
            )
    except EsoLogsApiError as exc:
        page._esologs_top_team_results = ()
        support._clear_esologs_evidence(page)
        page.status.error(str(exc))
    except Exception as exc:
        page._esologs_top_team_results = ()
        support._clear_esologs_evidence(page)
        page.status.error(f"ESO Logs refresh failed: {exc}")
    finally:
        page.refresh_esologs_button.setEnabled(True)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import comp_builder_build_candidate_support as candidate_support
    from ui import comp_builder_esologs_support as esologs_support

    original_chair_candidates = candidate_support._chair_candidates
    original_source_label = candidate_support._source_label

    def chair_candidates_with_esologs(page, row: int):
        base = tuple(original_chair_candidates(page, row))
        observed = _snapshot_candidates(page, row)
        combined = (*base, *observed)
        tier = {"saved_build": 0, "esologs_snapshot": 1, "reference_template": 2}
        return tuple(
            sorted(
                combined,
                key=lambda item: (
                    tier.get(item.source_kind, 3),
                    -item.score,
                    item.name.casefold(),
                    item.candidate_id.casefold(),
                ),
            )
        )

    def source_label_with_esologs(candidate: CompBuildCandidate) -> str:
        if candidate.source_kind == "esologs_snapshot":
            return f"ESO Logs snapshot • {candidate.source_name}"
        return original_source_label(candidate)

    candidate_support._chair_candidates = chair_candidates_with_esologs
    candidate_support._source_label = source_label_with_esologs
    esologs_support._refresh_live_esologs = _refresh_live_esologs_with_snapshots
    _INSTALLED = True
