"""Small dependency-boundary helpers used by architecture tests."""


def resolve_damage_bucket(*values: float) -> float:
    """Sum already-scoped DamageDone source buckets without cross-category mixing."""
    return sum(values)
