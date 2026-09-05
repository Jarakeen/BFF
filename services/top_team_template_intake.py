from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from models.top_team_model import TopTeamPlayer, TopTeamResult
from services.team_prescription_observed_templates import (
    ObservedTeamTemplate,
    ObservedTeamTemplateStore,
)
from services.top_team_service import TopTeamService


OBSERVED_TEAM_TEMPLATE_FILENAME = "team_prescription_observed_templates.json"


@dataclass(frozen=True)
class TopTeamTemplateIntakeResult:
    """Outcome of curating one ESO Logs player setup into Team Templates."""

    template: ObservedTeamTemplate
    mundus_lookup_requested: bool
    mundus_resolved: bool


@dataclass(frozen=True)
class TopTeamTemplateBatchIntakeResult:
    """Outcome of curating every usable player setup from one ranked team."""

    templates: tuple[ObservedTeamTemplate, ...]
    skipped_players: tuple[str, ...]


class TopTeamTemplateIntake:
    """UI-facing boundary for ``Add to Team Templates``.

    Performance owns choosing/fetching a ranked team. This service owns the handoff
    into persistent prescription evidence. It may resolve exactly one selected
    player's Mundus on demand, but it never mutates the fetched Top Team result or
    player and never promotes an observed setup into a complete canonical build.
    """

    def __init__(self, store: ObservedTeamTemplateStore):
        self.store = store

    @classmethod
    def for_data_dir(cls, data_dir: str | Path) -> "TopTeamTemplateIntake":
        """Construct the standard user-curated template intake for the app data dir."""

        return cls(
            ObservedTeamTemplateStore(
                Path(data_dir) / OBSERVED_TEAM_TEMPLATE_FILENAME
            )
        )

    def add_player(
        self,
        *,
        top_team_service: TopTeamService,
        result: TopTeamResult,
        player: TopTeamPlayer,
        game_update: str = "unresolved",
        retrieved_at: str | None = None,
        source_score: float = 100.0,
        include_mundus: bool = True,
    ) -> TopTeamTemplateIntakeResult:
        mundus_lookup_requested = bool(include_mundus and not player.Mundus.strip())
        mundus = player.Mundus.strip()

        if mundus_lookup_requested:
            mundus = top_team_service.resolve_player_mundus(result, player).strip()

        template_player = (
            replace(player, Mundus=mundus)
            if mundus != player.Mundus
            else player
        )
        template = self.store.add_top_team_player(
            result=result,
            player=template_player,
            game_update=game_update,
            retrieved_at=retrieved_at,
            source_score=source_score,
        )

        # The fetched Performance result remains evidence of the original API
        # response. Optional enrichment belongs only to the curated template.
        return TopTeamTemplateIntakeResult(
            template=template,
            mundus_lookup_requested=mundus_lookup_requested,
            mundus_resolved=bool(mundus),
        )

    def add_team(
        self,
        *,
        top_team_service: TopTeamService,
        result: TopTeamResult,
        game_update: str,
        retrieved_at: str | None = None,
        source_score: float = 100.0,
        include_mundus: bool = False,
    ) -> TopTeamTemplateBatchIntakeResult:
        """Curate every usable partial build in one fetched team.

        A player needs a resolved class plus at least one observed gear set or
        ability. Empty/anonymized rows are reported as skipped instead of becoming
        misleading catalog candidates. Mundus defaults off for bulk intake because
        resolving it would require an additional ESO Logs request per player.
        """

        templates: list[ObservedTeamTemplate] = []
        skipped: list[str] = []
        for player in result.Players:
            if not player.ClassName.strip() or not (
                player.GearSets or player.Abilities
            ):
                skipped.append(player.Name or "Unknown")
                continue
            outcome = self.add_player(
                top_team_service=top_team_service,
                result=result,
                player=player,
                game_update=game_update,
                retrieved_at=retrieved_at,
                source_score=source_score,
                include_mundus=include_mundus,
            )
            templates.append(outcome.template)
        return TopTeamTemplateBatchIntakeResult(
            templates=tuple(templates),
            skipped_players=tuple(skipped),
        )
