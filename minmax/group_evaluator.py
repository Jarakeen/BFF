from .group_evaluation import GroupEvaluation
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

        for source in roster:
            for effect in source.group_effects:

                if effect.effect_type != "damage_amplification":
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

                for candidate in affected_players:
                    group_damage += (
                        candidate.personal_damage
                        * effect.value
                        / 100.0
                        * effect.uptime
                    )

        return GroupEvaluation(
            group_damage=group_damage,
            support_score=0.0,
            survivability_score=0.0,
            mechanic_score=0.0,
        )