from .group_evaluation import (
    GroupEvaluation,
    PlayerDamageContribution,
    GroupEffectContribution,
)
from .roster import RosterCandidate
from .role import Role


class GroupEvaluator:

    def evaluate(
        self,
        roster: list[RosterCandidate],
    ) -> GroupEvaluation:

        personal_damage = sum(
            candidate.personal_damage
            for candidate in roster
        )

        group_damage = personal_damage
        player_contributions: list[PlayerDamageContribution] = []
        effect_contributions: list[GroupEffectContribution] = []
        unresolved_effects: list[str] = []

        # Track each player's baseline and supported damage
        player_supported_damage = {
            candidate.name: candidate.personal_damage
            for candidate in roster
        }

        for source in roster:
            for effect in source.group_effects:

                if effect.effect_type != "damage_amplification":
                    # Record unresolved non-damage effects
                    unresolved_effects.append(
                        f"{effect.effect_type} from {source.name}"
                    )
                    continue

                affected_players = [
                    candidate
                    for candidate in roster
                    if candidate.role in effect.affected_roles
                    and (
                        effect.affects_source
                        or candidate is not source
                    )
                ]

                recipient_names = tuple(c.name for c in affected_players)
                total_damage_added = 0.0

                for candidate in affected_players:
                    damage_added = (
                        candidate.personal_damage
                        * effect.value
                        / 100.0
                        * effect.uptime
                    )
                    group_damage += damage_added
                    total_damage_added += damage_added
                    player_supported_damage[candidate.name] += damage_added

                effect_contributions.append(
                    GroupEffectContribution(
                        source_name=source.name,
                        effect_source=effect.source,
                        effect_type=effect.effect_type,
                        value=effect.value,
                        uptime=effect.uptime,
                        recipient_names=recipient_names,
                        damage_added=total_damage_added,
                    )
                )

        # Build player contributions
        for candidate in roster:
            player_contributions.append(
                PlayerDamageContribution(
                    player_name=candidate.name,
                    baseline_damage=candidate.personal_damage,
                    supported_damage=player_supported_damage[candidate.name],
                )
            )

        return GroupEvaluation(
            group_damage=group_damage,
            support_score=0.0,
            survivability_score=0.0,
            mechanic_score=0.0,
            player_contributions=tuple(player_contributions),
            effect_contributions=tuple(effect_contributions),
            unresolved_effects=tuple(unresolved_effects),
        )