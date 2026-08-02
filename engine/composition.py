def evaluate_effect_coverage(encounter, roster):
	"""Return the roster players who provide each required encounter effect."""
	coverage = {effect: [] for effect in encounter.mechanics}

	for player in roster.players:
		provided_effects = {
			effect.capability_id
			for choice in player.choices
			for trigger in choice.triggers
			for effect in trigger.effects
		}

		for effect in coverage:
			if effect in provided_effects:
				coverage[effect].append(player.name)

	return coverage
