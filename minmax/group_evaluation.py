from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlayerDamageContribution:
    """Tracks a player's baseline and supported damage in a group evaluation."""
    player_name: str
    baseline_damage: float
    supported_damage: float


@dataclass(frozen=True)
class GroupEffectContribution:
    """Tracks how a single group effect contributes to group damage."""
    source_name: str
    effect_source: str
    effect_type: str
    value: float
    uptime: float
    recipient_names: tuple[str, ...]
    damage_added: float


@dataclass(frozen=True)
class GroupEvaluation:
    group_damage: float
    support_score: float
    survivability_score: float
    mechanic_score: float
    player_contributions: tuple[PlayerDamageContribution, ...] = ()
    effect_contributions: tuple[GroupEffectContribution, ...] = ()
    unresolved_effects: tuple[str, ...] = ()

    @property
    def baseline_damage(self) -> float:
        """Sum of all player baseline (personal) damage."""
        return sum(
            contrib.baseline_damage
            for contrib in self.player_contributions
        )

    @property
    def modeled_damage_delta(self) -> float:
        """Difference between modeled group damage and baseline damage."""
        return self.group_damage - self.baseline_damage